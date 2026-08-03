"""Events — class event log and broadcasting.

Records events like student_joined, class_started, poll_opened.
These feed the classroom timeline and CyberMentor context.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

MAX_EVENTS = 100

# {class_slug: deque[event]}
_events: dict[str, deque[dict[str, Any]]] = defaultdict(
    lambda: deque(maxlen=MAX_EVENTS))

EVENT_TYPES = (
    "student_joined", "student_left",
    "class_started", "class_ended",
    "poll_opened", "poll_closed",
    "resource_shared",
    "announcement",
    "hand_raised", "hand_lowered",
    "recording_started", "recording_ended",
)


def emit(class_slug: str, event_type: str,
         user_id: int = 0, username: str = "",
         data: dict[str, Any] | None = None) -> dict[str, Any]:
    event = {
        "type": event_type,
        "user_id": user_id,
        "username": username,
        "data": data or {},
        "timestamp": time.time(),
    }
    _events[class_slug].append(event)
    return event


def recent(class_slug: str, limit: int = 20) -> list[dict[str, Any]]:
    events = list(_events.get(class_slug, []))
    return events[-limit:]


def all_events(class_slug: str) -> list[dict[str, Any]]:
    return list(_events.get(class_slug, []))


def clear(class_slug: str) -> None:
    _events.pop(class_slug, None)
