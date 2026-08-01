"""Hint history — per-user per-objective tracking (in-memory)."""

from __future__ import annotations

import time
from collections import defaultdict

from app.core.ai.hints.models import HintRecord

# {user_id: {objective_id: [HintRecord, ...]}}
_history: dict[int, dict[int, list[HintRecord]]] = defaultdict(
    lambda: defaultdict(list))


def record(user_id: int, objective_id: int, lab_slug: str,
           level: int) -> HintRecord:
    """Record a hint request."""
    r = HintRecord(user_id=user_id, objective_id=objective_id,
                   lab_slug=lab_slug, level=level,
                   timestamp=time.time())
    _history[user_id][objective_id].append(r)
    return r


def get_history(user_id: int,
                objective_id: int) -> list[HintRecord]:
    return list(_history.get(user_id, {}).get(objective_id, []))


def current_level(user_id: int, objective_id: int) -> int:
    """Highest hint level already given for this objective."""
    records = get_history(user_id, objective_id)
    if not records:
        return 0
    return max(r.level for r in records)


def hint_count(user_id: int, objective_id: int) -> int:
    return len(_history.get(user_id, {}).get(objective_id, []))


def total_hints(user_id: int) -> int:
    """Total hints used across all objectives."""
    return sum(len(recs) for recs in
               _history.get(user_id, {}).values())


def mark_solved(user_id: int, objective_id: int) -> None:
    """Mark that the student solved the objective after hints."""
    for r in _history.get(user_id, {}).get(objective_id, []):
        r.solved_after = True


def all_records() -> list[HintRecord]:
    """All records across all users (for analytics)."""
    records: list[HintRecord] = []
    for user_recs in _history.values():
        for obj_recs in user_recs.values():
            records.extend(obj_recs)
    return records


def clear(user_id: int) -> None:
    _history.pop(user_id, None)


def clear_all() -> None:
    _history.clear()
