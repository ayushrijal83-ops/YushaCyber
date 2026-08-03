"""AI analytics charts — data series for frontend rendering.

Returns plain dicts that the existing analytics_charts.js can consume.
"""

from __future__ import annotations

from typing import Any

from app.core.ai.analytics.engine import get_dashboard


def ai_conversations_chart() -> dict[str, Any]:
    """Daily AI conversation counts (placeholder — extend with real time-series)."""
    d = get_dashboard()
    return {
        "chart": "ai_conversations",
        "labels": ["Today", "This Week", "This Month"],
        "values": [d.ai_usage.messages_today,
                   d.ai_usage.messages_week,
                   d.ai_usage.messages_month],
    }


def hint_usage_chart() -> dict[str, Any]:
    d = get_dashboard()
    dist = d.hints.level_distribution
    return {
        "chart": "hint_levels",
        "labels": [f"Level {k}" for k in sorted(dist.keys())],
        "values": [dist[k] for k in sorted(dist.keys())],
    }


def lab_completion_chart() -> dict[str, Any]:
    d = get_dashboard()
    completed = d.labs.most_completed[:5]
    return {
        "chart": "lab_completion",
        "labels": [c.get("title", "") for c in completed],
        "values": [c.get("count", 0) for c in completed],
    }


def student_progress_chart() -> dict[str, Any]:
    d = get_dashboard()
    return {
        "chart": "student_progress",
        "avg_xp": d.students.avg_xp,
        "avg_level": d.students.avg_level,
        "completion_rate": d.students.completion_rate,
        "total_active": d.students.total_active,
    }


def all_charts() -> list[dict[str, Any]]:
    return [
        ai_conversations_chart(),
        hint_usage_chart(),
        lab_completion_chart(),
        student_progress_chart(),
    ]
