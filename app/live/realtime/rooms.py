"""Room management — each class gets a room keyed by slug."""

from __future__ import annotations

import time
from typing import Any

# room_key → {user_ids, created_at, metadata}
_rooms: dict[str, dict[str, Any]] = {}


def room_key(class_slug: str) -> str:
    return f"classroom:{class_slug}"


def join(class_slug: str, user_id: int,
         username: str = "") -> None:
    key = room_key(class_slug)
    if key not in _rooms:
        _rooms[key] = {"users": {}, "created_at": time.time()}
    _rooms[key]["users"][user_id] = {
        "username": username,
        "joined_at": time.time(),
        "status": "online",
    }


def leave(class_slug: str, user_id: int) -> None:
    key = room_key(class_slug)
    if key in _rooms:
        _rooms[key]["users"].pop(user_id, None)
        if not _rooms[key]["users"]:
            _rooms.pop(key, None)


def members(class_slug: str) -> dict[int, dict[str, Any]]:
    key = room_key(class_slug)
    return dict((_rooms.get(key) or {}).get("users", {}))


def count(class_slug: str) -> int:
    return len(members(class_slug))


def is_in_room(class_slug: str, user_id: int) -> bool:
    return user_id in members(class_slug)


def all_rooms() -> dict[str, int]:
    return {k: len(v.get("users", {})) for k, v in _rooms.items()}
