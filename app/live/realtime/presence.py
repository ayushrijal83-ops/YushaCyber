"""Presence tracking — online/offline/idle status per user."""

from __future__ import annotations

import time
from typing import Any

IDLE_THRESHOLD = 120  # seconds

_presence: dict[str, dict[int, dict[str, Any]]] = {}


def update(class_slug: str, user_id: int,
           status: str = "online") -> None:
    key = f"classroom:{class_slug}"
    if key not in _presence:
        _presence[key] = {}
    _presence[key][user_id] = {
        "status": status,
        "last_seen": time.time(),
    }


def get_status(class_slug: str, user_id: int) -> str:
    key = f"classroom:{class_slug}"
    entry = (_presence.get(key) or {}).get(user_id)
    if not entry:
        return "offline"
    elapsed = time.time() - entry.get("last_seen", 0)
    if elapsed > IDLE_THRESHOLD:
        return "idle"
    return entry.get("status", "online")


def all_presence(class_slug: str) -> list[dict[str, Any]]:
    key = f"classroom:{class_slug}"
    result = []
    for uid, data in (_presence.get(key) or {}).items():
        elapsed = time.time() - data.get("last_seen", 0)
        status = data.get("status", "online")
        if elapsed > IDLE_THRESHOLD:
            status = "idle"
        result.append({
            "user_id": uid,
            "status": status,
            "last_seen": data.get("last_seen", 0),
        })
    return result


def remove(class_slug: str, user_id: int) -> None:
    key = f"classroom:{class_slug}"
    if key in _presence:
        _presence[key].pop(user_id, None)
