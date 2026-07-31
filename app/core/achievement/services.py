"""Achievement services — the public API.

Every module calls these functions instead of reaching into
submodules directly. Wraps the existing ``app/achievement/services``
for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from app.core.achievement.engine import (
    achievement_summary as _engine_summary,
    check_unlock,
)
from app.core.achievement.models import (
    achievement_from_orm,
)
from app.core.achievement.types import AchievementDef


# ---------------------------------------------------------------------------
# Registry — in-memory achievement definitions (for programmatic use).
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, AchievementDef] = {}


def register_achievement(achievement: AchievementDef) -> None:
    """Register an achievement definition in the in-memory registry."""
    _REGISTRY[achievement.slug] = achievement


def get_registered(slug: str) -> AchievementDef | None:
    return _REGISTRY.get(slug)


def all_registered() -> list[AchievementDef]:
    return list(_REGISTRY.values())


# ---------------------------------------------------------------------------
# Check + award (wraps existing ORM-based service).
# ---------------------------------------------------------------------------
def check_unlock_for_user(achievement: AchievementDef,
                          metrics: dict[str, Any]) -> bool:
    """Check whether a student meets the unlock requirements."""
    return check_unlock(achievement, metrics)


def award(user_id: int, achievement_slug: str) -> dict[str, Any]:
    """Award an achievement via the existing ORM service.

    Returns ``{"ok": True, ...}`` on success.
    """
    try:
        from app.achievement.models import Achievement as OrmAch
        from app.achievement.services import (
            has_achievement,
            unlock_achievement,
        )
        from app.auth.models import User
        user = User.query.get(user_id)
        orm_ach = OrmAch.query.filter_by(title=achievement_slug).first()
        if not user or not orm_ach:
            return {"ok": False, "reason": "not_found"}
        if has_achievement(user, orm_ach):
            return {"ok": False, "reason": "already_unlocked"}
        return unlock_achievement(user, orm_ach)
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}


def award_multiple(user_id: int,
                   metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Check and award all registered achievements for a student."""
    try:
        from app.achievement.services import check_and_unlock_achievements
        from app.auth.models import User
        user = User.query.get(user_id)
        if not user:
            return []
        result = check_and_unlock_achievements(user)
        return [{"title": a.title, "xp": a.bonus_xp}
                for a in (result.get("unlocked") or [])]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Listing + summary.
# ---------------------------------------------------------------------------
def list_student_achievements(user_id: int) -> list[dict[str, Any]]:
    """Return all achievements for a student via the ORM service."""
    try:
        from app.achievement.services import get_user_achievements
        from app.auth.models import User
        user = User.query.get(user_id)
        if not user:
            return []
        achievements = get_user_achievements(user)
        return [achievement_from_orm(a).to_dict() for a in achievements]
    except Exception:
        return []


def achievement_summary(achievements: list[AchievementDef],
                        unlocked_slugs: set[str] | None = None
                        ) -> dict[str, Any]:
    """Aggregate stats for display."""
    return _engine_summary(achievements, unlocked_slugs)
