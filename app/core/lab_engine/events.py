"""Lab events — universal event log per session."""

from __future__ import annotations

import time
from collections import deque
from typing import Any

MAX_EVENTS = 200


class EventLog:
    """Per-session event log."""

    def __init__(self) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=MAX_EVENTS)

    def emit(self, kind: str, data: dict[str, Any] | None = None
             ) -> dict[str, Any]:
        event = {"kind": kind, "data": data or {},
                 "timestamp": time.time()}
        self._events.append(event)
        return event

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._events)[-limit:]

    def all(self) -> list[dict[str, Any]]:
        return list(self._events)

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()

    def to_list(self) -> list[dict[str, Any]]:
        return list(self._events)

    @classmethod
    def from_list(cls, data: list[dict[str, Any]]) -> EventLog:
        log = cls()
        for e in data:
            log._events.append(e)
        return log
