"""Hand raise — queue management for live classrooms."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

# {class_slug: OrderedDict{user_id: info}}
_queues: dict[str, OrderedDict[int, dict[str, Any]]] = {}


def raise_hand(class_slug: str, user_id: int,
               username: str = "") -> dict[str, Any]:
    if class_slug not in _queues:
        _queues[class_slug] = OrderedDict()
    info = {"user_id": user_id, "username": username,
            "raised_at": time.time()}
    _queues[class_slug][user_id] = info
    return info


def lower_hand(class_slug: str, user_id: int) -> bool:
    if class_slug in _queues:
        return _queues[class_slug].pop(user_id, None) is not None
    return False


def get_queue(class_slug: str) -> list[dict[str, Any]]:
    if class_slug not in _queues:
        return []
    return list(_queues[class_slug].values())


def clear_queue(class_slug: str) -> int:
    if class_slug not in _queues:
        return 0
    count = len(_queues[class_slug])
    _queues[class_slug].clear()
    return count


def call_on(class_slug: str, user_id: int) -> dict[str, Any] | None:
    """Remove a student from the queue (instructor called on them)."""
    if class_slug in _queues:
        return _queues[class_slug].pop(user_id, None)
    return None


def is_raised(class_slug: str, user_id: int) -> bool:
    return user_id in _queues.get(class_slug, {})


def queue_count(class_slug: str) -> int:
    return len(_queues.get(class_slug, {}))
