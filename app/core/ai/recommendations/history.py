"""Recommendation history — tracks suggestions + outcomes."""

from __future__ import annotations

import time
from collections import defaultdict

from app.core.ai.recommendations.models import RecHistory

_history: dict[int, list[RecHistory]] = defaultdict(list)


def record(user_id: int, rec_type: str, slug: str,
           accepted: bool = False) -> None:
    _history[user_id].append(RecHistory(
        rec_type=rec_type, slug=slug, accepted=accepted,
        timestamp=time.time()))


def mark_completed(user_id: int, slug: str) -> None:
    for r in _history.get(user_id, []):
        if r.slug == slug:
            r.completed = True


def get_history(user_id: int,
                limit: int = 20) -> list[RecHistory]:
    return list(_history.get(user_id, []))[-limit:]


def acceptance_rate(user_id: int) -> float:
    recs = _history.get(user_id, [])
    if not recs:
        return 0.0
    accepted = sum(1 for r in recs if r.accepted)
    return round(accepted / len(recs), 2)


def clear(user_id: int) -> None:
    _history.pop(user_id, None)


def clear_all() -> None:
    _history.clear()
