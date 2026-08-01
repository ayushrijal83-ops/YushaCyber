"""Context builder — merges all collectors into FullContext."""

from __future__ import annotations

import time

from app.core.ai.context_engine import activity, collector
from app.core.ai.context_engine.models import FullContext

# Simple cache: (user_id, timestamp, context).
_cache: dict[int, tuple[float, FullContext]] = {}
CACHE_TTL = 10  # seconds


def build(user, current_lab: str = "",
          current_scenario: str = "",
          current_objective: str = "") -> FullContext:
    """Build the full context for an AI request.

    Cached for CACHE_TTL seconds per user to keep <100ms.
    """
    now = time.time()
    cache_key = user.id
    cached = _cache.get(cache_key)
    if cached and (now - cached[0]) < CACHE_TTL:
        ctx = cached[1]
        # Update volatile fields even from cache.
        ctx.learning.current_lab = current_lab
        ctx.learning.current_scenario = current_scenario
        ctx.learning.current_objective = current_objective
        ctx.activity = activity.get_activity(user.id)
        return ctx

    ctx = FullContext(
        user=collector.collect_user(user),
        learning=collector.collect_learning(
            user, current_lab, current_scenario, current_objective),
        progress=collector.collect_progress(user),
        achievements=collector.collect_achievements(user),
        assessment=collector.collect_assessment(user),
        roadmap=collector.collect_roadmap(user),
        activity=activity.get_activity(user.id),
    )
    _cache[cache_key] = (now, ctx)
    return ctx


def invalidate(user_id: int) -> None:
    """Clear cached context for a user (call after XP/lab changes)."""
    _cache.pop(user_id, None)


def invalidate_all() -> None:
    _cache.clear()
