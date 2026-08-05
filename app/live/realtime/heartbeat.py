"""Heartbeat — client keepalive tracking.

Clients send a heartbeat every 30 seconds. If no heartbeat for
120 seconds, the user is considered disconnected.
"""

from __future__ import annotations

import time

HEARTBEAT_INTERVAL = 30   # seconds between beats
TIMEOUT = 120             # seconds before disconnect

# {class_slug: {user_id: last_beat_timestamp}}
_beats: dict[str, dict[int, float]] = {}


def beat(class_slug: str, user_id: int) -> None:
    if class_slug not in _beats:
        _beats[class_slug] = {}
    _beats[class_slug][user_id] = time.time()


def is_alive(class_slug: str, user_id: int) -> bool:
    last = _beats.get(class_slug, {}).get(user_id, 0)
    return (time.time() - last) < TIMEOUT


def stale_users(class_slug: str) -> list[int]:
    """Return user_ids that have timed out."""
    now = time.time()
    return [uid for uid, ts in _beats.get(class_slug, {}).items()
            if (now - ts) >= TIMEOUT]


def remove(class_slug: str, user_id: int) -> None:
    if class_slug in _beats:
        _beats[class_slug].pop(user_id, None)


def clear(class_slug: str) -> None:
    _beats.pop(class_slug, None)
