"""Aggregator — builds typed summary dataclasses from raw data.

The aggregator sits between the raw metric helpers and the
service layer. It takes lists of dicts (from ORM queries or
API calls) and returns typed dataclass instances.
"""

from __future__ import annotations

from typing import Any

from app.core.analytics import metrics as m
from app.core.analytics.types import (
    AdminDashboard,
    AssessmentMetrics,
    EngagementMetrics,
    StudentMetrics,
    TrackMetrics,
)


def aggregate_student(data: dict[str, Any]) -> StudentMetrics:
    """Build StudentMetrics from a raw data dict."""
    total = data.get("total_labs", 0)
    completed = data.get("completed_labs", 0)
    scores = data.get("scores", [])
    return StudentMetrics(
        student_id=data.get("student_id", 0),
        username=data.get("username", ""),
        total_xp=data.get("total_xp", 0),
        xp_this_week=data.get("xp_this_week", 0),
        xp_this_month=data.get("xp_this_month", 0),
        level=data.get("level", 1),
        completed_labs=completed,
        total_labs=total,
        completed_tracks=data.get("completed_tracks", 0),
        completion_rate=m.completion_rate(completed, total),
        average_score=m.average(scores),
        average_grade=m.grade_from_scores(scores),
        average_time_seconds=int(m.average(
            data.get("times", []))),
        certificates_earned=data.get("certificates_earned", 0),
        achievements_earned=data.get("achievements_earned", 0),
        hints_used=data.get("hints_used", 0),
        attempts=data.get("attempts", 0),
        perfect_scores=data.get("perfect_scores", 0),
        current_streak=data.get("current_streak", 0),
        highest_streak=data.get("highest_streak", 0),
    )


def aggregate_track(data: dict[str, Any]) -> TrackMetrics:
    """Build TrackMetrics from a raw data dict."""
    return TrackMetrics(
        track_slug=data.get("track_slug", ""),
        track_name=data.get("track_name", ""),
        total_labs=data.get("total_labs", 0),
        completion_pct=m.completion_rate(
            data.get("completed", 0), data.get("total_labs", 0)),
        average_time_seconds=int(m.average(data.get("times", []))),
        difficulty_distribution=m.difficulty_distribution(
            data.get("difficulties", [])),
        most_completed_lab=data.get("most_completed_lab", ""),
        least_completed_lab=data.get("least_completed_lab", ""),
        enrolled_students=data.get("enrolled_students", 0),
    )


def aggregate_assessment(data: dict[str, Any]) -> AssessmentMetrics:
    """Build AssessmentMetrics from raw data."""
    scores = data.get("scores", [])
    grades = data.get("grades", [])
    passed = data.get("passed", 0)
    total = data.get("total_attempts", 0)
    pr, fr = m.pass_fail_rates(passed, total)
    return AssessmentMetrics(
        assessment_slug=data.get("assessment_slug", ""),
        total_attempts=total,
        pass_rate=pr,
        fail_rate=fr,
        average_grade=m.grade_from_scores(scores),
        grade_distribution=m.grade_distribution(grades),
        score_distribution=m.score_distribution(scores),
        average_attempts=m.average(data.get("attempts_list", [])),
        average_time_seconds=int(m.average(data.get("times", []))),
    )


def aggregate_engagement(data: dict[str, Any]) -> EngagementMetrics:
    """Build EngagementMetrics."""
    return EngagementMetrics(
        daily_active=data.get("daily_active", 0),
        weekly_active=data.get("weekly_active", 0),
        monthly_active=data.get("monthly_active", 0),
        average_streak=m.average(data.get("streaks", [])),
        average_study_minutes=m.average(
            data.get("study_minutes", [])),
    )


def aggregate_admin(data: dict[str, Any]) -> AdminDashboard:
    """Build AdminDashboard."""
    return AdminDashboard(
        total_students=data.get("total_students", 0),
        online_students=data.get("online_students", 0),
        total_xp_earned=data.get("total_xp_earned", 0),
        certificates_issued=data.get("certificates_issued", 0),
        achievements_unlocked=data.get("achievements_unlocked", 0),
        labs_completed=data.get("labs_completed", 0),
        top_students=data.get("top_students", []),
        most_popular_track=data.get("most_popular_track", ""),
        least_completed_track=data.get("least_completed_track", ""),
    )
