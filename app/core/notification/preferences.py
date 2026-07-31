"""Notification preferences — per-user settings.

Stored as a JSON blob on the user model (if available) or
defaults to all-enabled. No new table needed.
"""

from __future__ import annotations

from app.core.notification.types import CATEGORIES, UserPreferences


def get_preferences(user) -> UserPreferences:
    """Load preferences from a user object.

    Falls back to defaults if the user has no stored prefs.
    """
    raw = {}
    if hasattr(user, "notification_prefs_json"):
        import json
        try:
            raw = json.loads(user.notification_prefs_json or "{}")
        except (TypeError, ValueError):
            pass
    return UserPreferences(**{c: raw.get(c, True) for c in CATEGORIES})


def save_preferences(user, prefs: UserPreferences) -> None:
    """Save preferences to the user object (if field exists)."""
    if hasattr(user, "notification_prefs_json"):
        import json
        user.notification_prefs_json = json.dumps(prefs.to_dict())


def should_notify(user, category: str) -> bool:
    """Check if a user wants notifications in this category."""
    prefs = get_preferences(user)
    return prefs.allows(category)
