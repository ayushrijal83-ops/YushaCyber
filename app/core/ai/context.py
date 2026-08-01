"""Mentor context — auto-collects student context from ORM."""

from __future__ import annotations

from app.core.ai.types import MentorContext


def build_context(user, current_lab: str = "",
                  current_scenario: str = "",
                  current_difficulty: str = "") -> MentorContext:
    """Build mentor context from a User ORM object."""
    completed_labs: list[str] = []
    try:
        from app.labs.models import UserLabProgress
        progress = UserLabProgress.query.filter_by(
            user_id=user.id, completed=True).all()
        for p in progress:
            if hasattr(p, "lab") and p.lab:
                completed_labs.append(p.lab.slug)
    except Exception:
        pass

    achievements: list[str] = []
    try:
        from app.achievement.models import UserAchievement
        for ua in UserAchievement.query.filter_by(
                user_id=user.id).all():
            if hasattr(ua, "achievement") and ua.achievement:
                achievements.append(ua.achievement.title)
    except Exception:
        pass

    certificates: list[str] = []
    try:
        from app.certificates.models import UserCertificate
        for uc in UserCertificate.query.filter_by(
                user_id=user.id).all():
            if hasattr(uc, "certificate") and uc.certificate:
                certificates.append(uc.certificate.title)
    except Exception:
        pass

    return MentorContext(
        username=user.username,
        level=getattr(user, "level", 1),
        xp=getattr(user, "xp", 0),
        completed_labs=completed_labs,
        current_lab=current_lab,
        current_scenario=current_scenario,
        current_difficulty=current_difficulty,
        achievements=achievements,
        certificates=certificates,
    )


def context_from_dict(data: dict) -> MentorContext:
    """Build from a plain dict (for testing)."""
    return MentorContext(
        username=data.get("username", ""),
        level=data.get("level", 1),
        xp=data.get("xp", 0),
        completed_labs=data.get("completed_labs", []),
        current_lab=data.get("current_lab", ""),
        current_scenario=data.get("current_scenario", ""),
        current_difficulty=data.get("current_difficulty", ""),
        achievements=data.get("achievements", []),
        certificates=data.get("certificates", []),
    )
