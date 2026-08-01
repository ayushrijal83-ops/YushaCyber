"""Session tracker — navigation history per user."""

from __future__ import annotations

import time
from collections import deque
from typing import Any

MAX_HISTORY = 10

_sessions: dict[int, dict[str, Any]] = {}


def start_session(user_id: int) -> None:
    _sessions[user_id] = {
        "started_at": time.time(),
        "pages": deque(maxlen=MAX_HISTORY),
    }


def visit_page(user_id: int, path: str) -> None:
    if user_id not in _sessions:
        start_session(user_id)
    _sessions[user_id]["pages"].append({
        "path": path, "at": time.time()})


def get_session(user_id: int) -> dict[str, Any]:
    s = _sessions.get(user_id)
    if not s:
        return {"started_at": 0, "pages": [], "duration": 0}
    return {
        "started_at": s["started_at"],
        "pages": list(s["pages"]),
        "duration": int(time.time() - s["started_at"]),
    }


def end_session(user_id: int) -> None:
    _sessions.pop(user_id, None)
