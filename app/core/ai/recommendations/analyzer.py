"""Student analyzer — builds skill profile from ORM data."""

from __future__ import annotations

from app.core.ai.recommendations.models import SkillProfile


def analyze(user) -> SkillProfile:
    """Analyze a student's strengths, weaknesses, and readiness."""
    profile = SkillProfile()
    cat_rates: dict[str, float] = {}
    try:
        from app.labs.models import Lab, LabCategory, UserLabProgress
        categories = LabCategory.query.all()
        total_completed = 0
        total_labs = 0
        for cat in categories:
            labs = Lab.query.filter_by(
                category_id=cat.id, is_active=True).all()
            if not labs:
                continue
            done = sum(1 for lab in labs
                       if UserLabProgress.query.filter_by(
                           user_id=user.id, lab_id=lab.id,
                           completed=True).first())
            total_completed += done
            total_labs += len(labs)
            cat_rates[cat.name] = done / max(1, len(labs))
        if cat_rates:
            sorted_cats = sorted(cat_rates.items(),
                                 key=lambda x: x[1], reverse=True)
            profile.strongest_topics = [c[0] for c in sorted_cats[:3]
                                        if c[1] > 0]
            profile.weakest_topics = [c[0] for c in sorted_cats[-3:]
                                      if c[1] < 1.0]
        # Confidence: overall completion rate.
        profile.confidence = round(
            total_completed / max(1, total_labs), 2)
        # Readiness: based on XP + level.
        _ = getattr(user, "xp", 0)  # used for future scoring
        level = getattr(user, "level", 1)
        if level >= 50:
            profile.recommended_difficulty = "Expert"
        elif level >= 25:
            profile.recommended_difficulty = "Hard"
        elif level >= 10:
            profile.recommended_difficulty = "Medium"
        else:
            profile.recommended_difficulty = "Easy"
        profile.readiness_score = min(1.0, round(level / 100, 2))
    except Exception:
        pass
    return profile
