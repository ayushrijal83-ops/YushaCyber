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
