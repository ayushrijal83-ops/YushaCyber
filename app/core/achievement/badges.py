"""Badge generation helpers.

Builds Badge objects from AchievementDef instances. Wraps the
existing ``app/achievement/`` badge display logic.
"""

from __future__ import annotations


from app.core.achievement.types import AchievementDef, Badge, RARITY_COLORS


def generate_badge(achievement: AchievementDef,
                   unlocked_at: str = "") -> Badge:
    """Create a Badge from an achievement definition."""
    return Badge(
        title=achievement.title,
        description=achievement.description,
        rarity=achievement.rarity,
        icon=achievement.icon,
        color=achievement.badge_color
              or RARITY_COLORS.get(achievement.rarity, "#9e9e9e"),
        unlocked_at=unlocked_at,
    )


def generate_badges(achievements: list[AchievementDef],
                    unlocked_slugs: set[str] | None = None,
                    unlock_dates: dict[str, str] | None = None
                    ) -> list[Badge]:
    """Generate badges for a list of achievements.

    Only unlocked achievements (those in ``unlocked_slugs``) get
    a badge with a date; locked ones get an empty ``unlocked_at``.
    """
    unlocked_slugs = unlocked_slugs or set()
    unlock_dates = unlock_dates or {}
    badges = []
    for ach in achievements:
        if ach.slug in unlocked_slugs:
            badges.append(generate_badge(
                ach, unlock_dates.get(ach.slug, "")))
        else:
            badges.append(Badge(
                title=ach.title,
                description="Locked" if not ach.hidden else "???",
                rarity=ach.rarity,
                icon="🔒" if not ach.hidden else "❓",
                color="#444",
                unlocked_at="",
            ))
    return badges
