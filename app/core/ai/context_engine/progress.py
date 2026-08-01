"""Progress analyzer — compute structured learning profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LearningProfile:
    """Computed learning insights."""
    overall_completion: float = 0.0
    hint_dependency: str = "low"  # low | moderate | high
    completion_speed: str = "average"  # slow | average | fast
    weakest_topic: str = ""
    strongest_topic: str = ""
    recent_trend: str = "steady"  # improving | steady | declining

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_completion": self.overall_completion,
            "hint_dependency": self.hint_dependency,
            "completion_speed": self.completion_speed,
            "weakest_topic": self.weakest_topic,
            "strongest_topic": self.strongest_topic,
            "recent_trend": self.recent_trend,
        }


def analyze(user) -> LearningProfile:
    """Analyze a user's learning profile from ORM data."""
    profile = LearningProfile()
    try:
        from app.labs.models import Lab, UserLabProgress
        total = Lab.query.filter_by(is_active=True).count()
        completed = UserLabProgress.query.filter_by(
            user_id=user.id, completed=True).count()
        profile.overall_completion = round(
            completed / max(1, total), 2)
    except Exception:
        pass

    # Hint dependency from assessment results.
    try:
        from app.simulators.soc.models import AssessmentResult
        results = AssessmentResult.query.filter_by(
            user_id=user.id).all()
        if results:
            avg_hints = sum(
                getattr(r, "hints_used", 0) or 0
                for r in results) / max(1, len(results))
            if avg_hints > 5:
                profile.hint_dependency = "high"
            elif avg_hints > 2:
                profile.hint_dependency = "moderate"
    except Exception:
        pass

    # Category completion for weakest/strongest.
    try:
        from app.labs.models import Lab, LabCategory, UserLabProgress
        categories = LabCategory.query.all()
        cat_stats: dict[str, tuple[int, int]] = {}
        for cat in categories:
            cat_labs = Lab.query.filter_by(
                category_id=cat.id, is_active=True).all()
            if not cat_labs:
                continue
            done = sum(1 for lab in cat_labs
                       if UserLabProgress.query.filter_by(
                           user_id=user.id, lab_id=lab.id,
                           completed=True).first())
            cat_stats[cat.name] = (done, len(cat_labs))
        if cat_stats:
            rates = {name: d / max(1, t)
                     for name, (d, t) in cat_stats.items()}
            profile.strongest_topic = max(rates, key=rates.get)
            profile.weakest_topic = min(rates, key=rates.get)
    except Exception:
        pass

    return profile
