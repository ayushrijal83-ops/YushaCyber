"""Analytics services — the public API.

Every module calls these functions. Pure functions take raw data;
ORM-dependent functions are clearly marked.
"""

from __future__ import annotations

from typing import Any

from app.core.analytics.aggregator import (
    aggregate_admin,
    aggregate_assessment,
    aggregate_engagement,
    aggregate_student,
    aggregate_track,
)
from app.core.analytics.engine import (
    export_csv,
    export_json,
    generate_insights,
    generate_track_insights,
)
from app.core.analytics.types import (
    AdminDashboard,
    AssessmentMetrics,
    EngagementMetrics,
    Insight,
    StudentMetrics,
    TrackMetrics,
)


def student_summary(data: dict[str, Any]) -> StudentMetrics:
    """Build a student analytics summary from raw data."""
    return aggregate_student(data)


def student_summary_from_user(user) -> StudentMetrics:
    """Build a student summary from an ORM User (needs app context)."""
    from app.core.analytics.models import student_data_from_user
    return aggregate_student(student_data_from_user(user))


def track_summary(data: dict[str, Any]) -> TrackMetrics:
    """Build a track analytics summary."""
    return aggregate_track(data)


def assessment_summary(data: dict[str, Any]) -> AssessmentMetrics:
    """Build an assessment analytics summary."""
    return aggregate_assessment(data)


def engagement_summary(data: dict[str, Any]) -> EngagementMetrics:
    """Build engagement analytics."""
    return aggregate_engagement(data)


def admin_summary(data: dict[str, Any] | None = None
                  ) -> AdminDashboard:
    """Build admin dashboard summary.

    If ``data`` is None, fetches from the database (needs app context).
    """
    if data is None:
        from app.core.analytics.models import admin_data
        data = admin_data()
    return aggregate_admin(data)


def insights_for_student(student: StudentMetrics) -> list[Insight]:
    """Generate automatic learning insights."""
    return generate_insights(student)


def insights_for_track(track_data: dict[str, Any]) -> list[Insight]:
    """Generate track-level insights."""
    return generate_track_insights(track_data)


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------
def export_analytics_json(data: Any) -> str:
    return export_json(data)


def export_analytics_csv(rows: list[dict[str, Any]],
                         fieldnames: list[str] | None = None) -> str:
    return export_csv(rows, fieldnames)
