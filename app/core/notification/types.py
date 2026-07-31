"""Notification types — enums, priorities, and dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class NotificationType(str, Enum):
    ACHIEVEMENT = "achievement"
    XP_EARNED = "xp_earned"
    LEVEL_UP = "level_up"
    CERTIFICATE = "certificate"
    TRACK_COMPLETED = "track_completed"
    LAB_COMPLETED = "lab_completed"
    ASSESSMENT_PASSED = "assessment_passed"
    ASSESSMENT_FAILED = "assessment_failed"
    WEEKLY_REMINDER = "weekly_reminder"
    SYSTEM = "system"
    ADMIN_MESSAGE = "admin_message"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_ORDER = {"low": 0, "normal": 1, "high": 2, "critical": 3}

# Default type → priority mapping.
TYPE_PRIORITY: dict[str, str] = {
    "achievement": "normal",
    "xp_earned": "low",
    "level_up": "high",
    "certificate": "high",
    "track_completed": "normal",
    "lab_completed": "low",
    "assessment_passed": "high",
    "assessment_failed": "normal",
    "weekly_reminder": "low",
    "system": "critical",
    "admin_message": "high",
}

# Notification categories for preferences.
CATEGORIES = (
    "achievements", "xp", "certificates", "reminders",
    "announcements", "marketing",
)


@dataclass
class NotificationData:
    """In-memory notification — not an ORM model."""
    id: int | None = None
    user_id: int = 0
    title: str = ""
    message: str = ""
    type: str = "system"
    priority: str = "normal"
    category: str = ""
    link: str = ""
    created_at: str = ""
    read_at: str | None = None
    expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["is_read"] = self.is_read
        return d


@dataclass
class UserPreferences:
    """Per-user notification preferences."""
    achievements: bool = True
    xp: bool = True
    certificates: bool = True
    reminders: bool = True
    announcements: bool = True
    marketing: bool = False

    def allows(self, category: str) -> bool:
        return getattr(self, category, True)

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass
class DeliveryChannel:
    """Interface for a delivery channel (in-app, email, push, webhook)."""
    name: str = "in_app"
    enabled: bool = True

    def deliver(self, notification: NotificationData) -> bool:
        """Subclasses override. Returns True if delivered."""
        return self.enabled
