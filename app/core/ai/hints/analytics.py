"""Hint analytics — usage statistics."""

from __future__ import annotations

from collections import Counter

from app.core.ai.hints import history
from app.core.ai.hints.models import HintStats


def compute_stats() -> HintStats:
    """Compute platform-wide hint statistics."""
    records = history.all_records()
    if not records:
        return HintStats()

    total = len(records)
    levels = [r.level for r in records]
    avg_level = sum(levels) / max(1, total)

    # Per-objective counts.
    obj_counts: Counter[int] = Counter()
    for r in records:
        obj_counts[r.objective_id] += 1

    avg_per_obj = sum(obj_counts.values()) / max(1, len(obj_counts))

    # Most requested.
    most = [{"objective_id": oid, "count": cnt}
            for oid, cnt in obj_counts.most_common(10)]

    # Success rate (solved after hints).
    solved = sum(1 for r in records if r.solved_after)
    success_rate = round(solved / max(1, total), 2)

    return HintStats(
        total_requests=total,
        avg_hints_per_objective=round(avg_per_obj, 1),
        avg_level=round(avg_level, 1),
        most_requested_objectives=most,
        hint_success_rate=success_rate,
    )
