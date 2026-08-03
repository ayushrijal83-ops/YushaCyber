"""AI analytics engine — aggregation + caching."""

from __future__ import annotations

import time
from typing import Any

from app.core.ai.analytics.collector import (
    collect_ai_usage,
    collect_hints,
    collect_labs,
    collect_recommendations,
    collect_students,
)
from app.core.ai.analytics.models import AIHealthMetrics, DashboardData

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 30  # seconds


def _cached(key: str, fn, ttl: int = CACHE_TTL):
    now = time.time()
    if key in _cache and (now - _cache[key][0]) < ttl:
        return _cache[key][1]
    result = fn()
    _cache[key] = (now, result)
    return result


def get_dashboard() -> DashboardData:
    """Build the complete dashboard (cached)."""
    return _cached("dashboard", _build_dashboard)


def _build_dashboard() -> DashboardData:
    return DashboardData(
        ai_usage=collect_ai_usage(),
        students=collect_students(),
        hints=collect_hints(),
        recommendations=collect_recommendations(),
        labs=collect_labs(),
        health=_collect_health(),
    )


def _collect_health() -> AIHealthMetrics:
    try:
        from app.core.ai.config import get_config
        from app.core.ai.manager import get_manager
        cfg = get_config()
        mgr = get_manager()
        stats = mgr.usage()
        error_rate = (stats.failed_requests /
                      max(1, stats.total_requests))
        return AIHealthMetrics(
            provider=cfg.provider,
            model=cfg.model,
            status="ok" if cfg.enabled else "disabled",
            error_rate=round(error_rate, 2),
        )
    except Exception:
        return AIHealthMetrics(status="error")


def invalidate_cache() -> None:
    _cache.clear()
