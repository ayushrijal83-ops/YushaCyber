"""Announcements — broadcast, pin, dismiss."""

from __future__ import annotations

import time
from typing import Any

_announcements: dict[str, list[dict[str, Any]]] = {}


def broadcast(class_slug: str, text: str,
              instructor: str = "") -> dict[str, Any]:
    key = f"classroom:{class_slug}"
    ann = {
        "id": f"ann-{time.time_ns()}",
        "text": text[:500],
        "instructor": instructor,
        "pinned": False,
        "timestamp": time.time(),
    }
    if key not in _announcements:
        _announcements[key] = []
    _announcements[key].append(ann)
    return ann


def pin(class_slug: str, ann_id: str) -> bool:
    key = f"classroom:{class_slug}"
    for a in (_announcements.get(key) or []):
        if a["id"] == ann_id:
            a["pinned"] = True
            return True
    return False


def unpin(class_slug: str, ann_id: str) -> bool:
    key = f"classroom:{class_slug}"
    for a in (_announcements.get(key) or []):
        if a["id"] == ann_id:
            a["pinned"] = False
            return True
    return False


def get_all(class_slug: str) -> list[dict[str, Any]]:
    key = f"classroom:{class_slug}"
    return list(_announcements.get(key) or [])


def get_pinned(class_slug: str) -> list[dict[str, Any]]:
    return [a for a in get_all(class_slug) if a.get("pinned")]
