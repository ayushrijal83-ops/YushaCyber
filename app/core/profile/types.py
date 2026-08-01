"""Profile types — dataclasses, enums, and privacy controls."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Visibility(str, Enum):
    PUBLIC = "public"
    FRIENDS = "friends"  # future-ready
    PRIVATE = "private"


PROFILE_SECTIONS = (
    "overview", "level", "xp", "streak", "tracks", "labs",
    "achievements", "certificates", "activity", "statistics",
)


@dataclass
class SocialLinks:
    github: str = ""
    linkedin: str = ""
    website: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ProfileData:
    """In-memory profile — wraps ORM UserProfile + User."""
    user_id: int = 0
    username: str = ""
    display_name: str = ""
    headline: str = ""
    bio: str = ""
    avatar: str = ""
    country: str = ""
    joined_at: str = ""
    visibility: str = "public"
    verified: bool = False
    featured_certificate: str = ""
    featured_track: str = ""
    social_links: SocialLinks = field(default_factory=SocialLinks)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class PrivacySettings:
    """Per-section visibility toggles."""
    profile_visibility: str = "public"
    show_achievements: bool = True
    show_certificates: bool = True
    show_statistics: bool = True
    show_activity: bool = True
    show_streak: bool = True

    def section_visible(self, section: str) -> bool:
        mapping = {
            "achievements": self.show_achievements,
            "certificates": self.show_certificates,
            "statistics": self.show_statistics,
            "activity": self.show_activity,
            "streak": self.show_streak,
        }
        return mapping.get(section, True)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActivityItem:
    """One item in the activity feed."""
    type: str = ""       # achievement | certificate | track | level_up | assessment
    title: str = ""
    description: str = ""
    timestamp: str = ""
    icon: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProfileStatistics:
    """Computed stats for the profile page."""
    total_xp: int = 0
    level: int = 1
    completed_tracks: int = 0
    completed_labs: int = 0
    certificates_earned: int = 0
    achievements_earned: int = 0
    average_score: float = 0.0
    perfect_scores: int = 0
    learning_streak: int = 0
    study_time_hours: float = 0.0
    leaderboard_rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ShareData:
    """Metadata for sharing a profile."""
    public_url: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
