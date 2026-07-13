"""CTF service layer.

The single place CTF data is read and written. Flag comparison is
constant-time via the model's hashed flag. No XP awards, achievements, or
UI here — this foundation ticket records solves and reports stats only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from app.ctf.models import (
    Challenge,
    ChallengeCategory,
    ChallengeHint,
    ChallengeSolve,
)
from app.extensions import db


def get_categories() -> list[ChallengeCategory]:
    """All active categories in display order."""
    return (
        ChallengeCategory.query
        .filter_by(is_active=True)
        .order_by(ChallengeCategory.display_order)
        .all()
    )


def get_category(slug: str) -> Optional[ChallengeCategory]:
    """One active category by slug, or None."""
    if not slug:
        return None
    return ChallengeCategory.query.filter_by(slug=slug, is_active=True).first()


def get_all_challenges() -> list[Challenge]:
    """All active challenges in (category, display) order."""
    return (
        Challenge.query
        .filter_by(is_active=True)
        .order_by(Challenge.category_id, Challenge.display_order)
        .all()
    )


def get_challenge(slug: str) -> Optional[Challenge]:
    """One active challenge by slug, or None."""
    if not slug:
        return None
    return Challenge.query.filter_by(slug=slug, is_active=True).first()


def get_challenges_by_category(slug: str) -> list[Challenge]:
    """Active challenges in a category (by slug), in display order."""
    category = get_category(slug)
    if category is None:
        return []
    return (
        Challenge.query
        .filter_by(category_id=category.id, is_active=True)
        .order_by(Challenge.display_order)
        .all()
    )


def has_solved(user: User, challenge: Challenge) -> bool:
    """Whether the user has a solved record for this challenge."""
    if user is None or challenge is None:
        return False
    return (
        ChallengeSolve.query
        .filter_by(user_id=user.id, challenge_id=challenge.id, solved=True)
        .first()
        is not None
    )


def get_user_solves(user: User) -> list[ChallengeSolve]:
    """A user's solved challenge records, newest first."""
    if user is None:
        return []
    return (
        ChallengeSolve.query
        .filter_by(user_id=user.id, solved=True)
        .order_by(ChallengeSolve.solved_at.desc())
        .all()
    )


def _get_or_create_solve(user: User, challenge: Challenge) -> ChallengeSolve:
    """Fetch the user's solve row for a challenge, creating it if absent."""
    row = (
        ChallengeSolve.query
        .filter_by(user_id=user.id, challenge_id=challenge.id)
        .first()
    )
    if row is None:
        row = ChallengeSolve(
            user_id=user.id, challenge_id=challenge.id,
            solved=False, attempts=0,
        )
        db.session.add(row)
    return row


def submit_flag(user: User, challenge: Challenge,
                submitted_flag: str) -> dict[str, Any]:
    """Validate a flag submission, record the attempt, and reward first solves.

    Rules (YC-010.4):
    - Correct flag, never solved before -> mark solved, record solved_at,
      award ``challenge.xp_reward`` through the existing XP engine
      (award_xp, which recalculates level), then trigger the existing
      achievement service. XP is awarded exactly ONCE per challenge.
    - Correct flag, already solved -> no XP, no achievement trigger;
      returns already_solved=True.
    - Wrong flag -> nothing awarded; the attempt is still recorded.
    ``user.xp`` is never modified directly. The solve row and its XP are
    committed together, so a failure rolls back both — never a
    ChallengeSolve without XP, nor XP without a ChallengeSolve.

    Returns:
        {"correct": True,  "already_solved": False,
         "xp_awarded": int, "level_up": bool, "xp": int}
        {"correct": True,  "already_solved": True, "xp_awarded": 0}
        {"correct": False}                     (wrong flag)
        {"correct": False, "error": "invalid" | "persist_failed"}
    """
    if user is None or challenge is None or not challenge.is_active:
        return {"correct": False, "error": "invalid"}

    level_before = user.level or 1
    xp_awarded = 0
    first_solve = False

    try:
        row = _get_or_create_solve(user, challenge)
        row.attempts = (row.attempts or 0) + 1

        correct = challenge.check_flag(submitted_flag)
        # Capture prior state BEFORE marking solved, so a first solve is
        # distinguishable from a retry on an already-solved challenge.
        already_solved = bool(row.solved)

        if correct and not already_solved:
            first_solve = True
            row.solved = True
            row.solved_at = datetime.now(timezone.utc)

            # Award XP through the existing engine (never touch user.xp).
            # award_xp commits, persisting the solve row in the same
            # transaction — so solve + XP land together or not at all.
            if challenge.xp_reward:
                from app.dashboard.services import award_xp
                award_xp(user, challenge.xp_reward)
                xp_awarded = challenge.xp_reward
            else:
                db.session.commit()
        else:
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to record flag submission: user %s challenge %s",
            user.id, challenge.id,
        )
        return {"correct": False, "error": "persist_failed"}

    if not correct:
        return {"correct": False}

    if already_solved:
        current_app.logger.info(
            "CTF re-solve (no XP): user=%s challenge=%s already_solved=True",
            user.id, challenge.slug,
        )
        return {"correct": True, "already_solved": True, "xp_awarded": 0}

    # First solve: trigger the existing achievement engine (it computes its
    # own metrics and never double-unlocks).
    if first_solve:
        try:
            from app.achievement.services import check_and_unlock_achievements
            check_and_unlock_achievements(user)
        except Exception:  # noqa: BLE001 — never fail a solve on this
            current_app.logger.exception(
                "Achievement check failed after CTF solve: user %s", user.id
            )

    level_up = (user.level or 1) > level_before
    current_app.logger.info(
        "CTF solve: user=%s challenge=%s xp_awarded=%s level_up=%s",
        user.id, challenge.slug, xp_awarded, level_up,
    )
    return {
        "correct": True,
        "already_solved": False,
        "xp_awarded": xp_awarded,
        "level_up": level_up,
        "xp": challenge.xp_reward,
    }


def get_ctf_statistics(user: User) -> dict[str, int]:
    """CTF stats for a user: totals, solved/unsolved, completion, points.

    total_points sums the points of distinct solved challenges.
    """
    total = Challenge.query.filter_by(is_active=True).count()
    empty = {
        "total_challenges": total, "solved": 0, "unsolved": total,
        "completion_percentage": 0, "total_points": 0,
    }
    if user is None or total == 0:
        return empty

    solved_ids = [
        r.challenge_id
        for r in ChallengeSolve.query
        .filter_by(user_id=user.id, solved=True)
        .all()
    ]
    solved = len(solved_ids)
    unsolved = total - solved
    completion = int(solved / total * 100) if total else 0

    total_points = 0
    if solved_ids:
        total_points = (
            db.session.query(db.func.coalesce(db.func.sum(Challenge.points), 0))
            .filter(Challenge.id.in_(solved_ids))
            .scalar()
        ) or 0

    return {
        "total_challenges": total,
        "solved": solved,
        "unsolved": unsolved,
        "completion_percentage": completion,
        "total_points": total_points,
    }


# ===========================================================================
# Challenge browser page context (YC-010.2) — preformatted for the UI.
# Reuses get_categories/get_all_challenges/get_ctf_statistics/has_solved;
# no ORM leaks to the template.
# ===========================================================================
def get_ctf_page_context(user: User) -> dict[str, Any]:
    """Everything the CTF browser needs, grouped by category and preformatted.

    Returns {statistics, categories, has_any_challenges}. Each category is a
    plain dict with its challenge cards (including per-user solved status),
    so the template renders without touching the ORM.
    """
    stats = get_ctf_statistics(user)

    # Solved challenge ids for this user (one query), for O(1) status lookup.
    solved_ids: set[int] = set()
    if user is not None:
        solved_ids = {
            r.challenge_id
            for r in ChallengeSolve.query
            .filter_by(user_id=user.id, solved=True)
            .all()
        }

    categories: list[dict[str, Any]] = []
    for category in get_categories():
        cards: list[dict[str, Any]] = []
        for ch in category.challenges:
            if not ch.is_active:
                continue
            cards.append({
                "title": ch.title,
                "slug": ch.slug,
                "description": ch.description,
                "difficulty": ch.difficulty,
                "points": ch.points,
                "xp_reward": ch.xp_reward,
                "estimated_minutes": ch.estimated_minutes,
                "solved": ch.id in solved_ids,
            })
        categories.append({
            "name": category.name,
            "slug": category.slug,
            "icon": category.icon,
            "description": category.description,
            "challenges": cards,
        })

    total = stats["total_challenges"]
    return {
        "statistics": stats,
        "categories": categories,
        "has_any_challenges": total > 0,
        "nav_items": _ctf_nav_items(),
    }


def _ctf_nav_items() -> list:
    """Sidebar nav with the CTF item active (reuses dashboard nav)."""
    from app.dashboard.services import get_nav_items
    return get_nav_items(active="ctf")


# ===========================================================================
# Challenge detail page context (YC-010.3)
#
# SECURITY: the flag, its hash, and any solution metadata are NEVER included
# in the context — the client only ever receives public challenge fields.
# ===========================================================================
def _render_description(text: Optional[str]) -> str:
    """Render a challenge description as safe HTML (reuses the project's
    markdown renderer + sanitiser used by the lesson viewer)."""
    if not text:
        return ""
    import markdown as _markdown
    from app.roadmap.services import _sanitise_lesson_html

    html = _markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )
    return _sanitise_lesson_html(html)


def get_user_solve(user: User, challenge: Challenge) -> Optional[ChallengeSolve]:
    """The user's solve row for a challenge (solved or not), or None."""
    if user is None or challenge is None:
        return None
    return (
        ChallengeSolve.query
        .filter_by(user_id=user.id, challenge_id=challenge.id)
        .first()
    )


def get_challenge_page_context(user: User, category_slug: str,
                               challenge_slug: str) -> Optional[dict[str, Any]]:
    """Context for the challenge detail page, or None if not found.

    Never includes the flag or its hash. Returns the public challenge
    fields plus this user's solved state, attempt count, and solve date.
    """
    category = get_category(category_slug)
    if category is None:
        return None
    challenge = get_challenge(challenge_slug)
    if challenge is None or challenge.category_id != category.id:
        return None

    solve = get_user_solve(user, challenge)
    solved = has_solved(user, challenge)
    solved_at = solve.solved_at if (solve and solve.solved_at) else None

    return {
        "category": {"name": category.name, "slug": category.slug},
        "challenge": {
            "title": challenge.title,
            "slug": challenge.slug,
            "description_html": _render_description(challenge.description),
            "difficulty": challenge.difficulty,
            "points": challenge.points,
            "xp_reward": challenge.xp_reward,
            "estimated_minutes": challenge.estimated_minutes,
            "author": challenge.author,
            "hint": challenge.hint,
        },
        "hints": [
            {
                "title": h.title or f"Hint #{h.display_order}",
                "content": h.content,
                "order": h.display_order,
                "is_free": h.is_free,
            }
            for h in get_hints(challenge)
        ],
        "solved": solved,
        "attempts": solve.attempts if solve else 0,
        "solved_date": solved_at.strftime("%b %d, %Y") if solved_at else None,
        "nav_items": _ctf_nav_items(),
    }


# ===========================================================================
# Leaderboard (YC-010.5) — read-only aggregation over existing solve records.
#
# SECURITY: only public profile fields (username, profile_image, level, xp)
# ever leave this module. Email, password_hash, and other private fields are
# never selected.
# ===========================================================================
def _leaderboard_rows() -> list[dict[str, Any]]:
    """Aggregate every user's CTF standing, ranked.

    One grouped query over challenge_solves joined to users and challenges:
      - points  = SUM(challenge.points) over solved challenges
      - solved  = COUNT(solved challenges)
      - last_solved_at = MAX(solved_at)  (earliest finisher wins ties)

    Ranking: points DESC, then solves DESC, then earliest completion time
    (the user who reached their total first ranks higher).
    """
    total_challenges = Challenge.query.filter_by(is_active=True).count()

    rows = (
        db.session.query(
            User.id,
            User.username,
            User.profile_image,
            User.level,
            User.xp,
            db.func.coalesce(db.func.sum(Challenge.points), 0).label("points"),
            db.func.count(ChallengeSolve.id).label("solved"),
            db.func.max(ChallengeSolve.solved_at).label("finished_at"),
        )
        .join(ChallengeSolve, ChallengeSolve.user_id == User.id)
        .join(Challenge, ChallengeSolve.challenge_id == Challenge.id)
        .filter(ChallengeSolve.solved.is_(True), Challenge.is_active.is_(True))
        .group_by(User.id)
        .all()
    )

    entries: list[dict[str, Any]] = []
    for (uid, username, avatar, level, xp,
         points, solved, finished_at) in rows:
        entries.append({
            "user_id": uid,
            "username": username,
            "avatar": avatar,
            "level": level or 1,
            "xp": xp or 0,
            "points": int(points or 0),
            "solved": int(solved or 0),
            "completion": (
                int(solved / total_challenges * 100) if total_challenges else 0
            ),
            "finished_at": finished_at,
        })

    # Sort: points desc, solves desc, earliest finish first.
    # A NULL finish time sorts last among equals.
    def sort_key(e):
        f = e["finished_at"]
        return (
            -e["points"],
            -e["solved"],
            f.timestamp() if f is not None else float("inf"),
        )

    entries.sort(key=sort_key)
    for i, e in enumerate(entries, start=1):
        e["rank"] = i
    return entries


def get_leaderboard(limit: int = 100) -> list[dict[str, Any]]:
    """The top ``limit`` ranked CTF players (public fields only)."""
    entries = _leaderboard_rows()
    if limit is not None and limit > 0:
        return entries[:limit]
    return entries


def get_user_rank(user: User) -> Optional[int]:
    """A user's leaderboard rank, or None if they have no solves."""
    if user is None:
        return None
    for entry in _leaderboard_rows():
        if entry["user_id"] == user.id:
            return entry["rank"]
    return None


def get_leaderboard_page_context(user: User, page: int = 1,
                                 per_page: int = 25) -> dict[str, Any]:
    """Context for the leaderboard page: ranked rows, top cards, pagination."""
    entries = _leaderboard_rows()
    total_players = len(entries)
    total_solves = sum(e["solved"] for e in entries)

    # Pagination
    per_page = max(1, per_page)
    total_pages = max(1, (total_players + per_page - 1) // per_page)
    page = min(max(1, page), total_pages)
    start = (page - 1) * per_page
    page_rows = entries[start:start + per_page]

    # Mark the current user's row.
    for e in page_rows:
        e["is_current_user"] = (user is not None and e["user_id"] == user.id)

    champion = entries[0] if entries else None
    my_rank = get_user_rank(user)

    return {
        "rows": page_rows,
        "champion": champion,
        "total_players": total_players,
        "total_solves": total_solves,
        "my_rank": my_rank,
        "my_stats": get_ctf_statistics(user),
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_data": total_players > 0,
        "nav_items": _ctf_nav_items(),
    }


# ===========================================================================
# Hints (YC-010.6)
#
# Display-only: revealing a hint costs nothing today (no XP or point
# deduction). A penalty system may build on ``is_free`` later.
# ===========================================================================
def get_hints(challenge: Challenge) -> list[ChallengeHint]:
    """A challenge's hints in display order (empty list if none/missing)."""
    if challenge is None:
        return []
    return (
        ChallengeHint.query
        .filter_by(challenge_id=challenge.id)
        .order_by(ChallengeHint.display_order)
        .all()
    )


def get_hint(challenge: Challenge, order: int) -> Optional[ChallengeHint]:
    """One hint of a challenge by its display_order, or None."""
    if challenge is None or order is None:
        return None
    return (
        ChallengeHint.query
        .filter_by(challenge_id=challenge.id, display_order=order)
        .first()
    )
