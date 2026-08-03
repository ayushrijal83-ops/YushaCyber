"""AI analytics collector — gathers metrics from all subsystems."""

from __future__ import annotations

from app.core.ai.analytics.models import (
    AIHealthMetrics,
    AIUsageMetrics,
    HintAnalytics,
    LabAnalytics,
    RecommendationAnalytics,
    StudentAnalytics,
)


def collect_ai_usage() -> AIUsageMetrics:
    metrics = AIUsageMetrics()
    try:
        from app.core.ai.manager import get_manager
        mgr = get_manager()
        stats = mgr.usage()
        metrics.total_conversations = stats.total_requests
        metrics.avg_tokens = (stats.total_tokens // max(1, stats.total_requests))
        metrics.provider = stats.provider
        metrics.model = stats.model
    except Exception:
        pass
    return metrics


def collect_students() -> StudentAnalytics:
    metrics = StudentAnalytics()
    try:
        from app.auth.models import User
        from app.labs.models import Lab, UserLabProgress
        users = User.query.all()
        metrics.total_active = len(users)
        if users:
            metrics.avg_xp = sum(getattr(u, "xp", 0) for u in users) // max(1, len(users))
            metrics.avg_level = sum(getattr(u, "level", 1) for u in users) // max(1, len(users))
        total_labs = Lab.query.filter_by(is_active=True).count()
        total_completed = UserLabProgress.query.filter_by(completed=True).count()
        if total_labs and metrics.total_active:
            metrics.completion_rate = round(
                total_completed / (total_labs * metrics.total_active), 2)
        metrics.labs_completed = total_completed
    except Exception:
        pass
    return metrics


def collect_hints() -> HintAnalytics:
    metrics = HintAnalytics()
    try:
        from app.core.ai.hints import platform_stats
        stats = platform_stats()
        metrics.total_requested = stats.total_requests
        metrics.hint_success_rate = stats.hint_success_rate
        metrics.most_difficult_objectives = stats.most_requested_objectives[:5]
    except Exception:
        pass
    return metrics


def collect_recommendations() -> RecommendationAnalytics:
    metrics = RecommendationAnalytics()
    try:
        from app.core.ai.recommendations.history import get_stats
        stats = get_stats()
        metrics.total_generated = stats.get("generated", 0)
        metrics.accepted = stats.get("accepted", 0)
        metrics.ignored = stats.get("ignored", 0)
    except Exception:
        pass
    return metrics


def collect_labs() -> LabAnalytics:
    metrics = LabAnalytics()
    try:
        from app.labs.models import Lab, UserLabProgress
        labs = Lab.query.filter_by(is_active=True).all()
        metrics.total_labs = len(labs)
        if labs:
            completed_counts = []
            for lab in labs:
                count = UserLabProgress.query.filter_by(
                    lab_id=lab.id, completed=True).count()
                completed_counts.append((lab.title, lab.slug, count))
            completed_counts.sort(key=lambda x: x[2], reverse=True)
            metrics.most_completed = [
                {"title": t, "slug": s, "completions": c}
                for t, s, c in completed_counts[:5]]
            metrics.most_difficult = [
                {"title": t, "slug": s, "completions": c}
                for t, s, c in completed_counts[-5:]]
            total_completions = sum(c for _, _, c in completed_counts)
            total_users = max(1, len(set(
                p.user_id for p in UserLabProgress.query.all())))
            metrics.completion_rate = round(
                total_completions / (len(labs) * total_users), 2)
    except Exception:
        pass
    return metrics


def collect_health() -> AIHealthMetrics:
    metrics = AIHealthMetrics()
    try:
        from app.core.ai.manager import get_manager
        mgr = get_manager()
        h = mgr.health()
        metrics.provider = h.get("provider", "")
        metrics.model = h.get("model", "")
        metrics.status = h.get("status", "unknown")
        stats = mgr.usage()
        if stats.total_requests > 0:
            metrics.error_rate = round(
                stats.failed_requests / stats.total_requests, 3)
    except Exception:
        pass
    return metrics
