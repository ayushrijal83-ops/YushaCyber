"""Profile privacy — per-section visibility controls."""

from __future__ import annotations

from app.core.profile.types import PrivacySettings


def get_privacy(user) -> PrivacySettings:
    """Load privacy settings. Falls back to all-public defaults."""
    raw = {}
    if hasattr(user, "profile_privacy_json"):
        import json
        try:
            raw = json.loads(user.profile_privacy_json or "{}")
        except (TypeError, ValueError):
            pass
    return PrivacySettings(
        profile_visibility=raw.get("profile_visibility", "public"),
        show_achievements=raw.get("show_achievements", True),
        show_certificates=raw.get("show_certificates", True),
        show_statistics=raw.get("show_statistics", True),
        show_activity=raw.get("show_activity", True),
        show_streak=raw.get("show_streak", True),
    )


def is_visible(user, section: str) -> bool:
    """Check if a profile section is visible."""
    priv = get_privacy(user)
    if priv.profile_visibility == "private":
        return False
    return priv.section_visible(section)


def filter_sections(user, sections: dict) -> dict:
    """Remove hidden sections from a profile dict."""
    priv = get_privacy(user)
    if priv.profile_visibility == "private":
        return {"visibility": "private"}
    result = dict(sections)
    for key in list(result.keys()):
        if not priv.section_visible(key):
            del result[key]
    return result
