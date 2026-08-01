"""Context collector — gathers data from ORM models.

Each collect_* function reads from the database and returns
a typed context dataclass. All are safe to call without app
context (return defaults on error).
"""

from __future__ import annotations

from app.core.ai.context_engine.models import (
    AchievementContext,
    AssessmentContext,
    LearningContext,
    ProgressContext,
    RoadmapContext,
    UserContext,
)


def collect_user(user) -> UserContext:
    return UserContext(
        user_id=user.id,
        username=user.username,
        role="admin" if getattr(user, "is_admin", False) else "student",
    )


def collect_learning(user, current_lab: str = "",
                     current_scenario: str = "",
                     current_objective: str = "") -> LearningContext:
    lab_title = ""
    difficulty = ""
    if current_lab:
        try:
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug=current_lab).first()
            if lab:
                lab_title = lab.title
                difficulty = lab.difficulty
        except Exception:
            pass
    return LearningContext(
        current_lab=current_lab,
        current_lab_title=lab_title,
        current_scenario=current_scenario,
        current_objective=current_objective,
        difficulty=difficulty,
    )


def collect_progress(user) -> ProgressContext:
    completed = 0
    total = 0
    try:
        from app.labs.models import Lab, UserLabProgress
        total = Lab.query.filter_by(is_active=True).count()
        completed = UserLabProgress.query.filter_by(
            user_id=user.id, completed=True).count()
    except Exception:
        pass
    pct = round(completed / max(1, total), 2)
    return ProgressContext(
        xp=getattr(user, "xp", 0),
        level=getattr(user, "level", 1),
        completion_pct=pct,
        labs_completed=completed,
        total_labs=total,
        current_streak=getattr(user, "streak", 0),
    )


def collect_achievements(user) -> AchievementContext:
    recent: list[str] = []
    certs: list[str] = []
    total = 0
    try:
        from app.achievement.models import UserAchievement
        rows = (UserAchievement.query
                .filter_by(user_id=user.id)
                .order_by(UserAchievement.created_at.desc())
                .limit(5).all())
        recent = [ua.achievement.title for ua in rows
                  if hasattr(ua, "achievement") and ua.achievement]
        total = UserAchievement.query.filter_by(
            user_id=user.id).count()
    except Exception:
        pass
    try:
        from app.certificates.models import UserCertificate
        for uc in UserCertificate.query.filter_by(
                user_id=user.id).all():
            if hasattr(uc, "certificate") and uc.certificate:
                certs.append(uc.certificate.title)
    except Exception:
        pass
    return AchievementContext(
        recent_achievements=recent,
        certificates=certs,
        total_achievements=total,
    )


def collect_assessment(user) -> AssessmentContext:
    """Gather assessment performance data."""
    try:
        from app.simulators.soc.models import AssessmentResult
        results = AssessmentResult.query.filter_by(
            user_id=user.id).all()
        if results:
            scores = [r.score for r in results]
            return AssessmentContext(
                attempts=len(results),
                success_rate=round(
                    sum(1 for r in results if r.grade in
                        ("Excellent", "Pass", "A", "B", "C"))
                    / max(1, len(results)), 2),
                recent_scores=scores[-5:],
            )
    except Exception:
        pass
    return AssessmentContext()


def collect_roadmap(user) -> RoadmapContext:
    """Suggest next steps based on completion."""
    try:
        from app.labs.models import Lab, UserLabProgress
        completed_slugs = {
            p.lab.slug for p in
            UserLabProgress.query.filter_by(
                user_id=user.id, completed=True).all()
            if hasattr(p, "lab") and p.lab}
        next_lab = (Lab.query.filter_by(is_active=True)
                    .filter(~Lab.slug.in_(completed_slugs))
                    .order_by(Lab.display_order)
                    .first())
        return RoadmapContext(
            recommended_next=next_lab.title if next_lab else "All complete!",
        )
    except Exception:
        return RoadmapContext()
