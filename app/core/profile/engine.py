"""Profile engine — statistics computation + activity feed."""

from __future__ import annotations


from app.core.profile.types import ActivityItem, ProfileStatistics


def compute_statistics(user) -> ProfileStatistics:
    """Compute profile stats from ORM User + relationships."""
    from app.labs.models import UserLabProgress
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
    # Leaderboard rank.
    from app.auth.models import User
    rank = User.query.filter(User.xp > user.xp).count() + 1

    return ProfileStatistics(
        total_xp=getattr(user, "xp", 0),
        level=getattr(user, "level", 1),
        completed_labs=completed,
        certificates_earned=certs,
        achievements_earned=achievements,
        leaderboard_rank=rank,
    )


def recent_activity(user, limit: int = 10) -> list[ActivityItem]:
    """Build an activity feed from achievements + certificates."""
    items: list[ActivityItem] = []
    try:
        from app.achievement.models import UserAchievement
        for ua in (UserAchievement.query
                   .filter_by(user_id=user.id)
                   .order_by(UserAchievement.created_at.desc())
                   .limit(limit).all()):
            ach = ua.achievement
            items.append(ActivityItem(
                type="achievement",
                title=f"Unlocked: {ach.title}",
                description=ach.description or "",
                timestamp=str(ua.created_at) if ua.created_at else "",
                icon=ach.icon or "🏆",
            ))
    except Exception:
        pass
    try:
        from app.certificates.models import UserCertificate
        for uc in (UserCertificate.query
                   .filter_by(user_id=user.id)
                   .order_by(UserCertificate.created_at.desc())
                   .limit(limit).all()):
            cert = uc.certificate
            items.append(ActivityItem(
                type="certificate",
                title=f"Earned: {cert.title}",
                description=cert.description or "",
                timestamp=str(uc.created_at) if uc.created_at else "",
                icon="📜",
            ))
    except Exception:
        pass
    items.sort(key=lambda i: i.timestamp or "", reverse=True)
    return items[:limit]
