"""Team Engine (YC-034.0).

Team lifecycle (create / join / leave / invite / captain), the team
dashboard aggregates, and the team leaderboard. All learning stats are
aggregated live from the existing progress tables over member ids —
nothing is duplicated into team rows.

Rules:
  · a user belongs to at most one team
  · open teams are joinable directly; closed teams need an invite
  · the captain manages invites, settings and the captaincy itself
  · if the captain leaves, captaincy passes to the longest-serving
    member; an emptied team is deleted
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from app.achievement.models import UserAchievement
from app.auth.models import User
from app.certificates.models import UserCertificate
from app.community import notification_engine
from app.community.models import Team, TeamInvite, TeamMember
from app.ctf.models import ChallengeSolve
from app.extensions import db
from app.labs.models import UserLabProgress


class TeamError(ValueError):
    """User-facing team rule violation."""


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:70] or "team"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def membership_of(user_id: int) -> TeamMember | None:
    return TeamMember.query.filter_by(user_id=user_id).first()


def create_team(user: User, name: str, description: str = "",
                logo: str = "🛡️", is_open: bool = True) -> Team:
    name = (name or "").strip()
    if not 3 <= len(name) <= 60:
        raise TeamError("Team name must be 3–60 characters.")
    if membership_of(user.id):
        raise TeamError("You are already in a team — leave it first.")
    if Team.query.filter(func.lower(Team.name) == name.lower()).first():
        raise TeamError("A team with that name already exists.")
    slug = _slugify(name)
    if Team.query.filter_by(slug=slug).first():
        slug = f"{slug}-{Team.query.count() + 1}"

    team = Team(name=name, slug=slug,
                description=(description or "").strip() or None,
                logo=(logo or "🛡️")[:10], is_open=bool(is_open),
                captain_id=user.id)
    db.session.add(team)
    db.session.flush()
    db.session.add(TeamMember(team_id=team.id, user_id=user.id,
                              joined_at=_now()))
    db.session.commit()
    return team


def join_team(user: User, team: Team, *, via_invite: bool = False) -> None:
    if membership_of(user.id):
        raise TeamError("You are already in a team.")
    if not team.is_open and not via_invite:
        raise TeamError("This team is invite-only.")
    db.session.add(TeamMember(team_id=team.id, user_id=user.id,
                              joined_at=_now()))
    # Any live invite for this user is consumed by joining.
    TeamInvite.query.filter_by(team_id=team.id,
                               invitee_id=user.id).delete()
    if team.captain_id and team.captain_id != user.id:
        notification_engine.notify(
            [team.captain_id], "team_joined",
            f"{user.username} joined {team.name}",
            "Say hello on the team page.", f"/teams/{team.slug}")
    db.session.commit()


def leave_team(user: User) -> None:
    member = membership_of(user.id)
    if not member:
        raise TeamError("You are not in a team.")
    team = member.team
    db.session.delete(member)
    db.session.flush()
    remaining = (TeamMember.query.filter_by(team_id=team.id)
                 .order_by(TeamMember.joined_at.asc()).all())
    if not remaining:
        db.session.delete(team)
    elif team.captain_id == user.id:
        team.captain_id = remaining[0].user_id
    db.session.commit()


def invite(team: Team, inviter: User, invitee_username: str) -> TeamInvite:
    if team.captain_id != inviter.id:
        raise TeamError("Only the captain can send invites.")
    invitee = User.query.filter(
        func.lower(User.username) == (invitee_username or "").strip().lower()
    ).first()
    if not invitee:
        raise TeamError("No user with that username.")
    if membership_of(invitee.id):
        raise TeamError(f"{invitee.username} is already in a team.")
    if TeamInvite.query.filter_by(team_id=team.id,
                                  invitee_id=invitee.id).first():
        raise TeamError(f"{invitee.username} already has a pending invite.")
    team_invite = TeamInvite(team_id=team.id, inviter_id=inviter.id,
                             invitee_id=invitee.id)
    db.session.add(team_invite)
    notification_engine.notify(
        [invitee.id], "team_invite",
        f"Team invite: {team.name} {team.logo}",
        f"{inviter.username} invited you to join their team.",
        "/teams")
    db.session.commit()
    return team_invite


def accept_invite(user: User, team_invite: TeamInvite) -> Team:
    if team_invite.invitee_id != user.id:
        raise TeamError("This invite is not for you.")
    team = team_invite.team
    join_team(user, team, via_invite=True)
    return team


def decline_invite(user: User, team_invite: TeamInvite) -> None:
    if team_invite.invitee_id != user.id:
        raise TeamError("This invite is not for you.")
    db.session.delete(team_invite)
    db.session.commit()


def assign_captain(team: Team, actor: User, new_captain_id: int) -> None:
    if team.captain_id != actor.id and not actor.is_admin:
        raise TeamError("Only the captain can assign the captaincy.")
    if not TeamMember.query.filter_by(team_id=team.id,
                                     user_id=new_captain_id).first():
        raise TeamError("The new captain must be a team member.")
    team.captain_id = new_captain_id
    db.session.commit()


def update_team(team: Team, actor: User, *, description: str | None = None,
                logo: str | None = None,
                is_open: bool | None = None) -> None:
    if team.captain_id != actor.id and not actor.is_admin:
        raise TeamError("Only the captain can edit the team.")
    if description is not None:
        team.description = description.strip() or None
    if logo is not None and logo.strip():
        team.logo = logo.strip()[:10]
    if is_open is not None:
        team.is_open = bool(is_open)
    db.session.commit()


# ===========================================================================
# Aggregates — dashboard + leaderboard
# ===========================================================================
def team_stats(team: Team) -> dict[str, Any]:
    member_ids = [m.user_id for m in team.members]
    if not member_ids:
        return {"total_xp": 0, "avg_level": 0, "members": 0,
                "completed_labs": 0, "completed_ctfs": 0,
                "certificates": 0, "achievements": 0}
    xp_level = db.session.query(
        func.sum(User.xp), func.avg(User.level)).filter(
        User.id.in_(member_ids)).one()
    return {
        "total_xp": int(xp_level[0] or 0),
        "avg_level": round(float(xp_level[1] or 0), 1),
        "members": len(member_ids),
        "completed_labs": UserLabProgress.query.filter(
            UserLabProgress.user_id.in_(member_ids),
            UserLabProgress.completed.is_(True)).count(),
        "completed_ctfs": ChallengeSolve.query.filter(
            ChallengeSolve.user_id.in_(member_ids),
            ChallengeSolve.solved.is_(True)).count(),
        "certificates": UserCertificate.query.filter(
            UserCertificate.user_id.in_(member_ids)).count(),
        "achievements": UserAchievement.query.filter(
            UserAchievement.user_id.in_(member_ids)).count(),
    }


LEADERBOARD_METRICS = ("xp", "labs", "ctf", "achievements")


def leaderboard(metric: str = "xp") -> list[dict[str, Any]]:
    """All teams ranked by the chosen metric (aggregate SQL per metric,
    merged in Python — bounded by team count)."""
    if metric not in LEADERBOARD_METRICS:
        metric = "xp"

    xp = dict(db.session.query(
        TeamMember.team_id, func.coalesce(func.sum(User.xp), 0))
        .join(User, User.id == TeamMember.user_id)
        .group_by(TeamMember.team_id).all())
    members = dict(db.session.query(
        TeamMember.team_id, func.count(TeamMember.id))
        .group_by(TeamMember.team_id).all())
    labs = dict(db.session.query(
        TeamMember.team_id, func.count(UserLabProgress.id))
        .join(UserLabProgress,
              (UserLabProgress.user_id == TeamMember.user_id)
              & UserLabProgress.completed.is_(True))
        .group_by(TeamMember.team_id).all())
    ctf = dict(db.session.query(
        TeamMember.team_id, func.count(ChallengeSolve.id))
        .join(ChallengeSolve,
              (ChallengeSolve.user_id == TeamMember.user_id)
              & ChallengeSolve.solved.is_(True))
        .group_by(TeamMember.team_id).all())
    achievements = dict(db.session.query(
        TeamMember.team_id, func.count(UserAchievement.id))
        .join(UserAchievement,
              UserAchievement.user_id == TeamMember.user_id)
        .group_by(TeamMember.team_id).all())

    rows = []
    for team in Team.query.all():
        rows.append({
            "team": team,
            "members": members.get(team.id, 0),
            "xp": int(xp.get(team.id, 0)),
            "labs": labs.get(team.id, 0),
            "ctf": ctf.get(team.id, 0),
            "achievements": achievements.get(team.id, 0),
        })
    rows.sort(key=lambda r: (r[metric], r["xp"]), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows
