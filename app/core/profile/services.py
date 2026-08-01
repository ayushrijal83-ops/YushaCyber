"""Profile services — the public API."""

from __future__ import annotations

from typing import Any

from app.core.profile.engine import compute_statistics, recent_activity
from app.core.profile.models import profile_from_user
from app.core.profile.privacy import filter_sections
from app.core.profile.statistics import stats_to_display
from app.core.profile.types import (
    ProfileData,
    ProfileStatistics,
    ShareData,
)


def get_profile(user) -> ProfileData:
    """Load a user's profile data."""
    return profile_from_user(user)


def update_profile(user, data: dict[str, Any]) -> ProfileData:
    """Update profile fields on the ORM UserProfile.

    Creates the profile row if it doesn't exist.
    """
    from app.extensions import db
    from app.profiles.models import UserProfile
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
    if "bio" in data:
        profile.bio = str(data["bio"])[:500]
    if "country" in data:
        profile.country = str(data["country"])[:56]
    if "avatar" in data:
        profile.avatar_url = str(data["avatar"])[:500]
    if "github" in data:
        profile.github_url = str(data["github"])[:255]
    if "linkedin" in data:
        profile.linkedin_url = str(data["linkedin"])[:255]
    if "website" in data:
        profile.website_url = str(data["website"])[:255]
    db.session.flush()
    return profile_from_user(user)


def profile_statistics(user) -> ProfileStatistics:
    """Compute stats for a user's profile."""
    return compute_statistics(user)


def get_activity(user, limit: int = 10) -> list[dict[str, Any]]:
    """Recent activity feed."""
    return [a.to_dict() for a in recent_activity(user, limit)]


def share_link(user, base_url: str = "") -> ShareData:
    """Generate share metadata."""
    profile = profile_from_user(user)
    url = f"{base_url}/u/{profile.username}"
    return ShareData(
        public_url=url,
        og_title=f"{profile.display_name} — YushaCyber",
        og_description=(profile.bio[:160] if profile.bio
                        else f"Cybersecurity learner — Level {profile.user_id}"),
        og_image=profile.avatar or "",
    )


def profile_summary(user) -> dict[str, Any]:
    """Full profile summary for rendering."""
    profile = profile_from_user(user)
    stats = compute_statistics(user)
    activity = [a.to_dict() for a in recent_activity(user, 5)]
    sections = {
        "profile": profile.to_dict(),
        "statistics": stats_to_display(stats),
        "activity": activity,
        "achievements": [],  # populated by caller if visible
        "certificates": [],
    }
    filtered = filter_sections(user, sections)
    filtered["stats_raw"] = stats.to_dict()
    return filtered
