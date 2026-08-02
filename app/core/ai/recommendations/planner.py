"""Planner — generates daily and weekly study plans."""

from __future__ import annotations

from app.core.ai.recommendations.models import (
    DailyPlan,
    Recommendation,
    SkillProfile,
    WeeklyPlan,
)

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]


def daily_plan(recommendations: list[Recommendation],
               profile: SkillProfile) -> DailyPlan:
    """Build today's study plan from ranked recommendations."""
    top = recommendations[:3]
    review = ""
    if profile.weakest_topics:
        review = profile.weakest_topics[0]
    practice = ""
    challenge = ""
    stretch = ""
    for r in recommendations:
        if r.rec_type == "practice_lab" and not practice:
            practice = r.title
        elif r.rec_type == "advanced_topic" and not challenge:
            challenge = r.title
        elif r.rec_type == "certification_path" and not stretch:
            stretch = r.title
    return DailyPlan(
        recommendations=top,
        review_topic=review,
        practice_suggestion=practice,
        challenge=challenge,
        stretch_goal=stretch,
    )


def weekly_plan(recommendations: list[Recommendation],
                daily_minutes: int = 60) -> WeeklyPlan:
    """Distribute recommendations across the week."""
    plan: dict[str, list[Recommendation]] = {d: [] for d in WEEKDAYS}
    total_mins = 0
    total_xp = 0
    idx = 0
    for day in WEEKDAYS:
        day_mins = 0
        while idx < len(recommendations) and day_mins < daily_minutes:
            r = recommendations[idx]
            plan[day].append(r)
            day_mins += r.estimated_minutes or 30
            total_mins += r.estimated_minutes or 30
            total_xp += r.expected_xp
            idx += 1
    return WeeklyPlan(
        days=plan,
        total_estimated_minutes=total_mins,
        total_expected_xp=total_xp,
    )
