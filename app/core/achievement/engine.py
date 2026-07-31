"""Achievement engine — core unlock logic.

Stateless functions: check if an achievement should unlock,
generate badges, compute summaries.
"""

from __future__ import annotations

from typing import Any

from app.core.achievement.models import badge_from_achievement
from app.core.achievement.rules import evaluate_all
from app.core.achievement.types import AchievementDef, Badge, UnlockResult


def check_unlock(achievement: AchievementDef,
                 metrics: dict[str, Any],
                 already_unlocked: bool = False) -> UnlockResult:
    """Check whether an achievement should unlock given metrics."""
    if already_unlocked and not achievement.repeatable:
        return UnlockResult(already_had=True,
                            achievement_title=achievement.title)
    met = evaluate_all(achievement.requirements, metrics)
    if not met:
        return UnlockResult(achievement_title=achievement.title)
    badge = badge_from_achievement(achievement, unlocked=True)
    return UnlockResult(
        unlocked=True,
        achievement_title=achievement.title,
        xp_awarded=achievement.xp_reward,
        badge=badge,
    )


def check_multiple(achievements: list[AchievementDef],
                   metrics: dict[str, Any],
                   unlocked_titles: set[str] | None = None
                   ) -> list[UnlockResult]:
    """Check a batch of achievements, return only newly unlocked."""
    unlocked_titles = unlocked_titles or set()
    results = []
    for ach in achievements:
        already = ach.title in unlocked_titles
        result = check_unlock(ach, metrics, already)
        if result.unlocked:
            results.append(result)
    return results


def generate_badge(achievement: AchievementDef,
                   unlocked: bool = False,
                   unlocked_at: str = "") -> Badge:
    """Generate a badge for display."""
    return badge_from_achievement(achievement, unlocked, unlocked_at)


def achievement_summary(achievements: list[AchievementDef],
                        unlocked_titles: set[str]
                        ) -> dict[str, Any]:
    """Aggregate stats."""
    total = len(achievements)
    done = sum(1 for a in achievements if a.title in unlocked_titles)
    by_rarity: dict[str, dict[str, int]] = {}
    for a in achievements:
        r = a.rarity
        if r not in by_rarity:
            by_rarity[r] = {"total": 0, "unlocked": 0}
        by_rarity[r]["total"] += 1
        if a.title in unlocked_titles:
            by_rarity[r]["unlocked"] += 1
    return {
        "total": total,
        "unlocked": done,
        "locked": total - done,
        "completion_rate": round(done / max(1, total), 2),
        "total_xp": sum(a.xp_reward for a in achievements
                        if a.title in unlocked_titles),
        "by_rarity": by_rarity,
    }
