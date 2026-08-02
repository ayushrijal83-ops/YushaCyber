"""Personalized Learning Recommendations (YC-032.4).

    from app.core.ai.recommendations import (
        get_recommendations, get_skill_profile, get_daily_plan,
        get_weekly_plan, accept_recommendation, recommendation_history,
        Recommendation, SkillProfile, DailyPlan, WeeklyPlan,
    )
"""

from app.core.ai.recommendations.models import (  # noqa: F401
    DailyPlan,
    Recommendation,
    SkillProfile,
    WeeklyPlan,
)
from app.core.ai.recommendations.services import (  # noqa: F401
    accept_recommendation,
    get_daily_plan,
    get_recommendations,
    get_skill_profile,
    get_weekly_plan,
    recommendation_history,
)
