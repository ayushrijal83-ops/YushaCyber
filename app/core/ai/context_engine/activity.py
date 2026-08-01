"""Activity tracker — real-time student activity in memory."""

from __future__ import annotations

import time
from collections import deque
from typing import Any

from app.core.ai.context_engine.models import ActivityContext

MAX_RECENT = 5

_sessions: dict[int, dict[str, Any]] = {}


def track(user_id: int, action: str, page: str = "",
          lab: str = "", lesson: str = "") -> None:
    """Record a student activity event."""
    if user_id not in _sessions:
        _sessions[user_id] = {
            "started_at": time.time(),
            "current_page": "",
            "last_action": "",
            "pages": deque(maxlen=MAX_RECENT),
            "labs": deque(maxlen=MAX_RECENT),
            "lessons": deque(maxlen=MAX_RECENT),
        }
    s = _sessions[user_id]
    s["last_action"] = action
    if page:
        s["current_page"] = page
        if page not in s["pages"]:
            s["pages"].append(page)
    if lab and lab not in s["labs"]:
        s["labs"].append(lab)
    if lesson and lesson not in s["lessons"]:
        s["lessons"].append(lesson)


def get_activity(user_id: int) -> ActivityContext:
    """Return current activity context."""
    s = _sessions.get(user_id)
    if not s:
        return ActivityContext()
    elapsed = int(time.time() - s.get("started_at", time.time()))
    return ActivityContext(
        current_page=s.get("current_page", ""),
        time_spent_seconds=elapsed,
        last_action=s.get("last_action", ""),
        recent_pages=list(s.get("pages", [])),
        recent_labs=list(s.get("labs", [])),
        recent_lessons=list(s.get("lessons", [])),
    )


def clear(user_id: int) -> None:
    _sessions.pop(user_id, None)


def clear_all() -> None:
    _sessions.clear()
