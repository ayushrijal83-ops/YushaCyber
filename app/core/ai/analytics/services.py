"""AI analytics services — the public API."""

from __future__ import annotations

from typing import Any

from app.core.ai.analytics.charts import all_charts
from app.core.ai.analytics.engine import get_dashboard, invalidate_cache
from app.core.ai.analytics.export import export_csv, export_json
from app.core.ai.analytics.models import DashboardData
from app.core.ai.analytics.reports import (
    daily_report,
    monthly_report,
    student_report,
    weekly_report,
)


def dashboard_metrics() -> DashboardData:
    """Full dashboard data (cached)."""
    return get_dashboard()


def dashboard_dict() -> dict[str, Any]:
    return get_dashboard().to_dict()


def get_report(period: str = "daily", user=None) -> dict[str, Any]:
    if period == "weekly":
        return weekly_report()
    if period == "monthly":
        return monthly_report()
    if period == "student" and user:
        return student_report(user)
    return daily_report()


def get_charts() -> list[dict[str, Any]]:
    return all_charts()


def export_data(dataset: str = "all",
                fmt: str = "json") -> str:
    if fmt == "csv":
        return export_csv(dataset)
    return export_json(dataset)


def refresh() -> None:
    invalidate_cache()
