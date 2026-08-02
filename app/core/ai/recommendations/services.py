"""Recommendation services — the public API."""

from __future__ import annotations

from typing import Any

from app.core.ai.recommendations.analyzer import analyze as build_skill_profile
from app.core.ai.recommendations.engine import generate
from app.core.ai.recommendations.history import (
    acceptance_rate,
    get_history,
    mark_completed,
    record,
)
from app.core.ai.recommendations.models import (
    DailyPlan,
    Recommendation,
    SkillProfile,
    WeeklyPlan,
)
from app.core.ai.recommendations.planner import daily_plan as build_daily_plan


def get_recommendations(user, limit: int = 5
                        ) -> list[Recommendation]:
    """Top recommendations for a student."""
    return generate(user, limit)


def get_recommendations_dict(user, limit: int = 5
                             ) -> list[dict[str, Any]]:
    return [r.to_dict() for r in get_recommendations(user, limit)]


def get_skill_profile(user) -> SkillProfile:
    return build_skill_profile(user)


def get_daily_plan(user) -> DailyPlan:
    recs = generate(user, 3)
    return build_daily_plan(recs, build_skill_profile(user))


def get_weekly_plan(user) -> WeeklyPlan:
    """Simple weekly plan: same daily plan for each day."""
    daily = get_daily_plan(user)
    days = {}
    for day in ("Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"):
        days[day] = daily
    return WeeklyPlan(days=days)


def accept_recommendation(user_id: int, slug: str) -> None:
    record(user_id, "accepted", slug, accepted=True)


def complete_recommendation(user_id: int, slug: str) -> None:
    mark_completed(user_id, slug)


def recommendation_history(user_id: int) -> list[dict[str, Any]]:
    return [r.to_dict() for r in get_history(user_id)]


def recommendation_summary(user) -> dict[str, Any]:
    recs = get_recommendations(user, 3)
    profile = build_skill_profile(user)
    return {
        "recommendations": [r.to_dict() for r in recs],
        "skill_profile": profile.to_dict(),
        "acceptance_rate": acceptance_rate(user.id),
    }
