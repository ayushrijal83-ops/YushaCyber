"""Lab state — session save, restore, and reset."""

from __future__ import annotations

from typing import Any

# In-memory state store: {(user_id, lab_slug): state_dict}
_states: dict[tuple[int, str], dict[str, Any]] = {}


def save(user_id: int, lab_slug: str,
         state: dict[str, Any]) -> None:
    _states[(user_id, lab_slug)] = state


def load(user_id: int, lab_slug: str) -> dict[str, Any] | None:
    return _states.get((user_id, lab_slug))


def reset(user_id: int, lab_slug: str) -> None:
    _states.pop((user_id, lab_slug), None)


def has_state(user_id: int, lab_slug: str) -> bool:
    return (user_id, lab_slug) in _states


def clear_all() -> None:
    _states.clear()
