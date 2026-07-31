"""Achievement types — enums, rarity tiers, and dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Rarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


RARITY_COLORS: dict[str, str] = {
    "common": "#8b95a5",
    "rare": "#3b82f6",
    "epic": "#a855f7",
    "legendary": "#f59e0b",
    "mythic": "#ef4444",
}


class UnlockCondition(str, Enum):
    """Built-in unlock condition types."""
    COMPLETE_SCENARIO = "complete_scenario"
    COMPLETE_TRACK = "complete_track"
    PERFECT_SCORE = "perfect_score"
    SPEED_RUN = "speed_run"
    XP_MILESTONE = "xp_milestone"
    LEVEL_MILESTONE = "level_milestone"
    CERTIFICATE_EARNED = "certificate_earned"
    LAB_COMPLETED = "lab_completed"
    SOC_LAB_COMPLETED = "soc_lab_completed"
    CUSTOM = "custom"


@dataclass
class AchievementDef:
    """In-memory achievement definition — NOT an ORM model."""
    id: int | None = None
    slug: str = ""
    title: str = ""
    description: str = ""
    category: str = "general"
    icon: str = "award"
    rarity: str = "common"
    xp_reward: int = 0
    badge_color: str = ""
    hidden: bool = False
    repeatable: bool = False
    requirements: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d["badge_color"]:
            d["badge_color"] = RARITY_COLORS.get(self.rarity, "#8b95a5")
        return d


@dataclass
class Badge:
    """Rendered badge object for display."""
    title: str = ""
    description: str = ""
    rarity: str = "common"
    icon: str = "award"
    color: str = ""
    unlocked: bool = False
    unlocked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UnlockResult:
    """Result of an unlock check."""
    unlocked: bool = False
    achievement_title: str = ""
    xp_awarded: int = 0
    badge: Badge | None = None
    already_had: bool = False
