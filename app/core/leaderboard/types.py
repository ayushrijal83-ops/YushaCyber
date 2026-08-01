"""Leaderboard types — dataclasses, enums, and ranking config."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Season(str, Enum):
    ALL_TIME = "all_time"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Category(str, Enum):
    GLOBAL = "global"
    COUNTRY = "country"
    TRACK = "track"
    MODULE = "module"
    FRIENDS = "friends"


class RankMetric(str, Enum):
    XP = "xp"
    LEVEL = "level"
    CERTIFICATES = "certificates"
    ACHIEVEMENTS = "achievements"
    COMPLETED_TRACKS = "completed_tracks"
    COMPLETED_LABS = "completed_labs"
    AVERAGE_SCORE = "average_score"
    PERFECT_SCORES = "perfect_scores"
    FASTEST_TIME = "fastest_time"
    STREAK = "streak"
    COMPOSITE = "composite"


# Tie-breaker order (highest priority first).
TIE_BREAKERS = ("xp", "certificates", "achievements",
                "average_score", "joined_at_asc")


@dataclass
class LeaderboardEntry:
    """One row on the leaderboard."""
    rank: int = 0
    user_id: int = 0
    username: str = ""
    display_name: str = ""
    avatar: str = ""
    country: str = ""
    level: int = 1
    xp: int = 0
    score: float = 0.0
    certificates: int = 0
    achievements: int = 0
    completed_labs: int = 0
    completed_tracks: int = 0
    streak: int = 0
    trend: str = "➜"  # ▲ ▼ ➜

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LeaderboardPage:
    """A paginated leaderboard result."""
    entries: list[LeaderboardEntry] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 25
    season: str = "all_time"
    metric: str = "xp"
    user_rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "season": self.season,
            "metric": self.metric,
            "user_rank": self.user_rank,
        }


@dataclass
class SeasonInfo:
    """Season metadata."""
    key: str = "all_time"
    label: str = "All Time"
    start_date: str = ""
    end_date: str = ""
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
