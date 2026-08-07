"""Lab state — session save/load/reset (in-memory)."""

from __future__ import annotations

from typing import Any

_store: dict[tuple[int, str], dict[str, Any]] = {}


def save(user_id: int, slug: str, data: dict[str, Any]) -> None:
    _store[(user_id, slug)] = data


def load(user_id: int, slug: str) -> dict[str, Any] | None:
    return _store.get((user_id, slug))


def reset(user_id: int, slug: str) -> None:
    _store.pop((user_id, slug), None)


def exists(user_id: int, slug: str) -> bool:
    return (user_id, slug) in _store


def clear_all() -> None:
    _store.clear()
