"""Profile models — ORM bridge.

Reads from existing User + UserProfile models and builds
ProfileData dataclasses. No new tables.
"""

from __future__ import annotations

from app.core.profile.types import ProfileData, SocialLinks


def profile_from_user(user) -> ProfileData:
    """Build a ProfileData from a User ORM object."""
    profile = getattr(user, "public_profile", None)
    social = SocialLinks()
    if profile:
        social = SocialLinks(
            github=profile.github_url or "",
            linkedin=profile.linkedin_url or "",
            website=profile.website_url or "",
        )
    return ProfileData(
        user_id=user.id,
        username=user.username,
        display_name=getattr(user, "display_name", "") or user.username,
        headline="",
        bio=(profile.bio if profile else "") or "",
        avatar=(profile.avatar_url if profile else "") or "",
        country=(profile.country if profile else "") or "",
        joined_at=str(user.created_at) if user.created_at else "",
        visibility="public",
        verified=getattr(user, "is_admin", False),
        social_links=social,
    )


def profile_from_dict(data: dict) -> ProfileData:
    """Build from a plain dict."""
    return ProfileData(
        user_id=data.get("user_id", 0),
        username=data.get("username", ""),
        display_name=data.get("display_name", ""),
        headline=data.get("headline", ""),
        bio=data.get("bio", ""),
        avatar=data.get("avatar", ""),
        country=data.get("country", ""),
        joined_at=data.get("joined_at", ""),
        visibility=data.get("visibility", "public"),
        verified=data.get("verified", False),
        featured_certificate=data.get("featured_certificate", ""),
        featured_track=data.get("featured_track", ""),
        social_links=SocialLinks(**data.get("social_links", {})),
    )
