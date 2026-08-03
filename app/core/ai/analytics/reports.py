"""AI analytics reports — structured report generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.ai.analytics.engine import get_dashboard


def daily_report() -> dict[str, Any]:
    d = get_dashboard()
    return {
        "type": "daily",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ai_messages_today": d.ai_usage.messages_today,
        "total_hints": d.hints.total_requested,
        "labs_completed": d.labs.completion_rate,
        "active_students": d.students.total_active,
        "health_status": d.health.status,
    }


def weekly_report() -> dict[str, Any]:
    d = get_dashboard()
    return {
        "type": "weekly",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ai_messages_week": d.ai_usage.messages_week,
        "total_hints": d.hints.total_requested,
        "hint_success_rate": d.hints.hint_success_rate,
        "completion_rate": d.labs.completion_rate,
        "avg_xp": d.students.avg_xp,
        "avg_level": d.students.avg_level,
        "weakest_topics": d.recommendations.weakest_topics,
        "strongest_topics": d.recommendations.strongest_topics,
        "health": d.health.to_dict(),
    }


def monthly_report() -> dict[str, Any]:
    d = get_dashboard()
    return {
        "type": "monthly",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": d.to_dict(),
    }


def student_report(user) -> dict[str, Any]:
    """Per-student report."""
    try:
        from app.core.ai.context_engine import get_context_dict
        ctx = get_context_dict(user)
    except Exception:
        ctx = {}
    try:
        from app.core.ai.recommendations import get_skill_profile
        profile = get_skill_profile(user).to_dict()
    except Exception:
        profile = {}
    return {
        "type": "student",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user.id,
        "username": user.username,
        "context": ctx,
        "skill_profile": profile,
    }
