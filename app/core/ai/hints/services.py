"""Hint services — the public API."""

from __future__ import annotations

from typing import Any

from app.core.ai.hints.analytics import compute_stats
from app.core.ai.hints.engine import request_hint
from app.core.ai.hints.history import (
    current_level,
    get_history,
    hint_count,
    total_hints,
)
from app.core.ai.hints.models import HintResponse, HintStats


def get_hint(user_id: int, objective_id: int,
             is_admin: bool = False) -> HintResponse:
    """Request a hint."""
    return request_hint(user_id, objective_id, is_admin)


def hint_summary(user_id: int,
                 objective_id: int) -> dict[str, Any]:
    """Summary for a specific objective."""
    return {
        "current_level": current_level(user_id, objective_id),
        "hint_count": hint_count(user_id, objective_id),
        "total_user_hints": total_hints(user_id),
        "history": [r.to_dict()
                    for r in get_history(user_id, objective_id)],
    }


def platform_stats() -> HintStats:
    """Platform-wide hint analytics."""
    return compute_stats()
