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
from app.ctf.models import Challenge, ChallengeCategory, ChallengeSolve
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
    """Validate a flag submission and record the attempt.

    Compares the submitted flag against the challenge's hashed flag,
    creates or updates the user's ChallengeSolve, increments attempts, and
    on a first correct solve marks it solved with a timestamp. Does NOT
    award XP (that integration comes later). Returns:
        {"correct": True,  "xp": challenge.xp_reward, "already_solved": bool}
        {"correct": False, "error": "invalid"}   (bad input)
        {"correct": False}                        (wrong flag)
    Rolls back on persistence failure.
    """
    if user is None or challenge is None or not challenge.is_active:
        return {"correct": False, "error": "invalid"}

    try:
        row = _get_or_create_solve(user, challenge)
        row.attempts = (row.attempts or 0) + 1

        correct = challenge.check_flag(submitted_flag)
        already_solved = bool(row.solved)

        if correct and not row.solved:
            row.solved = True
            row.solved_at = datetime.now(timezone.utc)

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to record flag submission: user %s challenge %s",
            user.id, challenge.id,
        )
        return {"correct": False, "error": "persist_failed"}

    if correct:
        return {"correct": True, "xp": challenge.xp_reward,
                "already_solved": already_solved}
    return {"correct": False}


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
        "solved": solved,
        "attempts": solve.attempts if solve else 0,
        "solved_date": solved_at.strftime("%b %d, %Y") if solved_at else None,
        "nav_items": _ctf_nav_items(),
    }
