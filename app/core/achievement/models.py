"""Achievement models — bridges between ORM and the framework.

Factory functions that build AchievementDef objects from existing
ORM Achievement rows, preserving backward compatibility.
"""

from __future__ import annotations

from typing import Any

from app.core.achievement.types import AchievementDef, Badge, RARITY_COLORS


def achievement_from_orm(orm_obj) -> AchievementDef:
    """Build an AchievementDef from an ORM Achievement row."""
    condition_type = getattr(orm_obj, "condition_type", "") or ""
    condition_value = getattr(orm_obj, "condition_value", 0) or 0
    requirements = []
    if condition_type:
        requirements.append({
            "type": condition_type,
            "value": condition_value,
        })
    return AchievementDef(
        id=orm_obj.id,
        slug=getattr(orm_obj, "slug", "") or getattr(orm_obj, "title", ""),
        title=orm_obj.title,
        description=getattr(orm_obj, "description", "") or "",
        category=getattr(orm_obj, "category", "general") or "general",
        icon=getattr(orm_obj, "icon", "award") or "award",
        rarity=_infer_rarity(getattr(orm_obj, "bonus_xp", 0) or 0),
        xp_reward=getattr(orm_obj, "bonus_xp", 0) or 0,
        requirements=requirements,
    )


def achievement_from_dict(data: dict[str, Any]) -> AchievementDef:
    """Build an AchievementDef from a plain dict."""
    return AchievementDef(
        id=data.get("id"),
        slug=data.get("slug", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        category=data.get("category", "general"),
        icon=data.get("icon", "award"),
        rarity=data.get("rarity", "common"),
        xp_reward=data.get("xp_reward", 0),
        badge_color=data.get("badge_color", ""),
        hidden=data.get("hidden", False),
        repeatable=data.get("repeatable", False),
        requirements=data.get("requirements", []),
    )


def badge_from_achievement(ach: AchievementDef,
                           unlocked: bool = False,
                           unlocked_at: str = "") -> Badge:
    """Build a displayable Badge from an AchievementDef."""
    return Badge(
        title=ach.title,
        description=ach.description,
        rarity=ach.rarity,
        icon=ach.icon,
        color=ach.badge_color or RARITY_COLORS.get(ach.rarity, ""),
        unlocked=unlocked,
        unlocked_at=unlocked_at,
    )


def _infer_rarity(xp_reward: int) -> str:
    """Infer rarity from XP reward for backward-compat ORM rows."""
    if xp_reward >= 250:
        return "legendary"
    if xp_reward >= 150:
        return "epic"
    if xp_reward >= 50:
        return "rare"
    if xp_reward >= 25:
        return "common"
    return "common"
