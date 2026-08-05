"""Live chat — in-memory message store per classroom."""

from __future__ import annotations

import time
from collections import deque
from typing import Any

MAX_HISTORY = 100

_chats: dict[str, deque] = {}


def send(class_slug: str, user_id: int, username: str,
         text: str, role: str = "student") -> dict[str, Any]:
    key = f"classroom:{class_slug}"
    if key not in _chats:
        _chats[key] = deque(maxlen=MAX_HISTORY)
    msg = {
        "id": f"{key}-{time.time_ns()}",
        "user_id": user_id,
        "username": username,
        "text": text[:500],
        "role": role,
        "timestamp": time.time(),
        "deleted": False,
    }
    _chats[key].append(msg)
    return msg


def history(class_slug: str, limit: int = 50) -> list[dict[str, Any]]:
    key = f"classroom:{class_slug}"
    msgs = list(_chats.get(key) or [])
    return [m for m in msgs[-limit:] if not m.get("deleted")]


def delete_message(class_slug: str, msg_id: str,
                   user_id: int, is_instructor: bool = False
                   ) -> bool:
    key = f"classroom:{class_slug}"
    for msg in (_chats.get(key) or []):
        if msg["id"] == msg_id:
            if msg["user_id"] == user_id or is_instructor:
                msg["deleted"] = True
                return True
    return False


def clear(class_slug: str) -> None:
    key = f"classroom:{class_slug}"
    _chats.pop(key, None)
