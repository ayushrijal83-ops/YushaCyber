"""Analytics models — ORM bridge builders.

These read from existing ORM models (User, Lab, Achievement, etc.)
and produce raw data dicts that the aggregator consumes. This is the
only file that touches the database.
"""

from __future__ import annotations

from typing import Any


def student_data_from_user(user) -> dict[str, Any]:
    """Build a raw data dict from a User ORM object.

    Works with the existing User model — reads xp, level, and
    counts completions from relationships.
    """
    from app.labs.models import Lab, UserLabProgress
    total_labs = Lab.query.filter_by(is_active=True).count()
    completed = UserLabProgress.query.filter_by(
        user_id=user.id, completed=True).count()
    certs = 0
    try:
        from app.certificates.models import UserCertificate
        certs = UserCertificate.query.filter_by(
            user_id=user.id).count()
    except Exception:
        pass
    achievements = 0
    try:
        from app.achievement.models import UserAchievement
        achievements = UserAchievement.query.filter_by(
            user_id=user.id).count()
    except Exception:
        pass
    return {
        "student_id": user.id,
        "username": user.username,
        "total_xp": getattr(user, "xp", 0),
        "level": getattr(user, "level", 1),
        "completed_labs": completed,
        "total_labs": total_labs,
        "certificates_earned": certs,
        "achievements_earned": achievements,
        "scores": [],
        "times": [],
    }


def admin_data() -> dict[str, Any]:
    """Build raw admin dashboard data from the database."""
    from app.auth.models import User
    from app.labs.models import UserLabProgress
    total_students = User.query.count()
    labs_completed = UserLabProgress.query.filter_by(
        completed=True).count()
    total_xp = sum(u.xp for u in User.query.all()
                   if hasattr(u, "xp"))
    certs_issued = 0
    try:
        from app.certificates.models import UserCertificate
        certs_issued = UserCertificate.query.count()
    except Exception:
        pass
    achievements_unlocked = 0
    try:
        from app.achievement.models import UserAchievement
        achievements_unlocked = UserAchievement.query.count()
    except Exception:
        pass
    top = []
    for u in User.query.order_by(User.xp.desc()).limit(10).all():
        top.append({"username": u.username,
                    "xp": getattr(u, "xp", 0),
                    "level": getattr(u, "level", 1)})
    return {
        "total_students": total_students,
        "total_xp_earned": total_xp,
        "certificates_issued": certs_issued,
        "achievements_unlocked": achievements_unlocked,
        "labs_completed": labs_completed,
        "top_students": top,
    }
