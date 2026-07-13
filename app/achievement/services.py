"""Achievement service layer.

The single place achievement data is read and written. No automatic
unlocking, XP awards, or UI here — this foundation ticket provides
retrieval, a duplicate-safe manual unlock, and statistics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.achievement.models import Achievement, UserAchievement
from app.auth.models import User
from app.extensions import db


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def get_all_achievements() -> list[Achievement]:
    """All active achievements in display order."""
    return (
        Achievement.query
        .filter_by(is_active=True)
        .order_by(Achievement.display_order)
        .all()
    )


def get_user_achievements(user: User) -> list[Achievement]:
    """The active achievements this user has unlocked, in display order."""
    if user is None:
        return []
    return (
        Achievement.query
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .filter(
            UserAchievement.user_id == user.id,
            Achievement.is_active.is_(True),
        )
        .order_by(Achievement.display_order)
        .all()
    )


def has_achievement(user: User, achievement: Achievement) -> bool:
    """Whether the user has already unlocked this achievement."""
    if user is None or achievement is None:
        return False
    return (
        UserAchievement.query
        .filter_by(user_id=user.id, achievement_id=achievement.id)
        .first()
        is not None
    )


def unlock_achievement(user: User, achievement: Achievement) -> dict[str, Any]:
    """Unlock an achievement for a user, once.

    Creates a UserAchievement only if not already unlocked. Never
    duplicates (guarded by the check and the unique constraint). Does NOT
    award bonus XP here — that belongs to the later auto-unlock ticket.

    Returns {unlocked: bool, achievement: Achievement | None}. ``unlocked``
    is True only when a new row was created this call.
    """
    result = {"unlocked": False, "achievement": achievement}

    if user is None or achievement is None:
        return result

    if has_achievement(user, achievement):
        return result  # already unlocked — no duplicate, unlocked stays False

    try:
        row = UserAchievement(
            user_id=user.id,
            achievement_id=achievement.id,
            unlocked_at=_utcnow(),
        )
        db.session.add(row)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to unlock achievement %s for user %s",
            achievement.id, user.id,
        )
        return result

    result["unlocked"] = True
    return result


def get_locked_achievements(user: User) -> list[Achievement]:
    """Active achievements the user has NOT yet unlocked, in display order."""
    all_active = get_all_achievements()
    if user is None:
        return all_active

    unlocked_ids = {
        row.achievement_id
        for row in UserAchievement.query.filter_by(user_id=user.id).all()
    }
    return [a for a in all_active if a.id not in unlocked_ids]


def get_achievement_statistics(user: User) -> dict[str, int]:
    """Unlock stats for a user: total, unlocked, locked, percentage."""
    total = Achievement.query.filter_by(is_active=True).count()
    if user is None or total == 0:
        return {"total": total, "unlocked": 0, "locked": total, "percentage": 0}

    unlocked = len(get_user_achievements(user))
    locked = total - unlocked
    percentage = int(unlocked / total * 100) if total else 0
    return {
        "total": total,
        "unlocked": unlocked,
        "locked": locked,
        "percentage": percentage,
    }


# ===========================================================================
# Automatic unlocking (YC-008.2)
# ===========================================================================
def _user_progress_metrics(user: User) -> dict[str, int]:
    """Compute the progress metrics achievements are evaluated against.

    Reuses existing services (no duplicated logic): lesson progress from
    UserLessonProgress, quiz stats from quiz_services, module completion
    from roadmap services, and level/xp from the user record.
    """
    from app.roadmap.models import UserLessonProgress
    from app.roadmap.services import (
        get_all_categories,
        get_modules,
        is_module_completed,
    )
    from app.roadmap.quiz_services import get_quiz_statistics

    lessons_completed = (
        UserLessonProgress.query
        .filter_by(user_id=user.id, completed=True)
        .count()
    )

    quiz_stats = get_quiz_statistics(user)

    # Distinct modules this user has completed.
    modules_completed = 0
    for category in get_all_categories():
        for module in get_modules(category.id):
            if is_module_completed(user, module):
                modules_completed += 1

    # Did any attempt score 100%? (best_score is the max percentage.)
    perfect = 1 if quiz_stats.get("best_score", 0) >= 100 else 0

    return {
        "lessons_completed": lessons_completed,
        "quizzes_passed": quiz_stats.get("quizzes_passed", 0),
        "level_reached": user.level or 1,
        "xp_earned": user.xp or 0,
        "perfect_quiz": perfect,
        "modules_completed": modules_completed,
    }


# Map each supported condition_type (both the seed's names and the
# ticket's shorthand) to the metric key it is measured against.
_CONDITION_METRIC = {
    "lessons_completed": "lessons_completed",
    "lesson_completed": "lessons_completed",
    "quizzes_passed": "quizzes_passed",
    "quiz_passed": "quizzes_passed",
    "level_reached": "level_reached",
    "level": "level_reached",
    "xp_earned": "xp_earned",
    "xp": "xp_earned",
    "perfect_quiz": "perfect_quiz",
    "perfect_score": "perfect_quiz",
    "modules_completed": "modules_completed",
    "module_completed": "modules_completed",
}


def check_and_unlock_achievements(user: User) -> dict[str, Any]:
    """Unlock every achievement the user now qualifies for.

    Inspects current progress, compares against each active achievement's
    condition, and unlocks any newly earned ones (never duplicating).
    Awards each newly unlocked achievement's bonus_xp through the existing
    XP engine. Returns {"unlocked": [Achievement, ...]} — only the
    achievements unlocked on THIS call.
    """
    result: dict[str, Any] = {"unlocked": []}
    if user is None:
        return result

    metrics = _user_progress_metrics(user)

    for achievement in get_all_achievements():
        if has_achievement(user, achievement):
            continue

        metric_key = _CONDITION_METRIC.get(achievement.condition_type)
        if metric_key is None:
            continue  # unknown condition — skip rather than error

        if metrics.get(metric_key, 0) >= achievement.condition_value:
            outcome = unlock_achievement(user, achievement)
            if outcome["unlocked"]:
                # Award the achievement's bonus XP through the engine.
                if achievement.bonus_xp:
                    from app.dashboard.services import award_xp
                    award_xp(user, achievement.bonus_xp)
                    # Bonus XP may itself satisfy an xp_earned achievement;
                    # refresh the metric so a chained unlock can happen below.
                    metrics["xp_earned"] = user.xp or 0
                result["unlocked"].append(achievement)

    return result


# ===========================================================================
# Dashboard page context (YC-008.3) — preformatted for the achievements UI.
# Reuses the retrieval + statistics services; no ORM leaks to the template.
# ===========================================================================
def get_achievements_page_context(user: User) -> dict[str, Any]:
    """Everything the achievements page needs, preformatted.

    Returns {statistics, achievements, has_any_unlocked}. Each achievement
    is a plain dict with an ``unlocked`` flag and a formatted unlock date,
    so the template renders without touching the ORM or computing anything.
    """
    stats = get_achievement_statistics(user)

    # Map achievement_id -> unlock datetime for this user (one query).
    unlocked_at: dict[int, Any] = {}
    if user is not None:
        for row in UserAchievement.query.filter_by(user_id=user.id).all():
            unlocked_at[row.achievement_id] = row.unlocked_at or row.created_at

    cards: list[dict[str, Any]] = []
    for a in get_all_achievements():
        when = unlocked_at.get(a.id)
        cards.append({
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "icon": a.icon,
            "category": a.category,
            "bonus_xp": a.bonus_xp,
            "unlocked": a.id in unlocked_at,
            "unlocked_date": when.strftime("%b %d, %Y") if when else None,
        })

    return {
        "statistics": stats,
        "achievements": cards,
        "has_any_unlocked": stats["unlocked"] > 0,
        "nav_items": _achievements_nav_items(),
    }


def _achievements_nav_items() -> list:
    """Sidebar nav with the achievements item active (reuses dashboard nav)."""
    from app.dashboard.services import get_nav_items
    return get_nav_items(active="achievements")
