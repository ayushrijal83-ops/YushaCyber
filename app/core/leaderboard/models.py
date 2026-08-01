"""Leaderboard models — ORM bridge.

Reads from existing User model + lab progress to build
LeaderboardEntry dataclasses. No new tables.
"""

from __future__ import annotations

from app.core.leaderboard.types import LeaderboardEntry


def entry_from_user(user, rank: int = 0) -> LeaderboardEntry:
    """Build a LeaderboardEntry from a User ORM object."""
    profile = getattr(user, "public_profile", None)
    certs = 0
    try:
        from app.certificates.models import UserCertificate
        certs = UserCertificate.query.filter_by(user_id=user.id).count()
    except Exception:
        pass
    achievements = 0
    try:
        from app.achievement.models import UserAchievement
        achievements = UserAchievement.query.filter_by(
            user_id=user.id).count()
    except Exception:
        pass
    from app.labs.models import UserLabProgress
    labs = UserLabProgress.query.filter_by(
        user_id=user.id, completed=True).count()
    return LeaderboardEntry(
        rank=rank,
        user_id=user.id,
        username=user.username,
        display_name=getattr(user, "display_name", "") or user.username,
        avatar=(profile.avatar_url if profile else "") or "",
        country=(profile.country if profile else "") or "",
        level=getattr(user, "level", 1),
        xp=getattr(user, "xp", 0),
        certificates=certs,
        achievements=achievements,
        completed_labs=labs,
        streak=getattr(user, "streak", 0),
    )


def all_entries() -> list[LeaderboardEntry]:
    """Build entries for every active user."""
    from app.auth.models import User
    users = User.query.order_by(User.xp.desc()).all()
    return [entry_from_user(u, rank=i)
            for i, u in enumerate(users, 1)]
