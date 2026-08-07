"""Lab engine services — the public API.

Every module calls these instead of reaching into submodules.
"""

from __future__ import annotations

from typing import Any

from app.core.lab_engine import engine
from app.core.lab_engine.registry import (
    list_labs,
    registered_types,
)


def start_lab(user_id: int, slug: str) -> dict[str, Any]:
    session = engine.start(user_id, slug)
    if session is None:
        return {"error": f"Lab '{slug}' not found."}
    return session.to_dict()


def submit_objective(user_id: int, slug: str,
                     objective_id: str,
                     submission: str = "") -> dict[str, Any]:
    result = engine.submit(user_id, slug, objective_id, submission)
    return result.to_dict()


def use_hint(user_id: int, slug: str,
             objective_id: str = "") -> None:
    engine.hint(user_id, slug, objective_id)


def reset_lab(user_id: int, slug: str) -> dict[str, Any]:
    session = engine.reset(user_id, slug)
    if session is None:
        return {"error": "Lab not found."}
    return session.to_dict()


def get_session(user_id: int, slug: str) -> dict[str, Any] | None:
    session = engine.get_session(user_id, slug)
    return session.to_dict() if session else None


def get_ai_context(user_id: int, slug: str) -> dict[str, Any]:
    return engine.ai_context(user_id, slug)


def available_labs(lab_type: str | None = None) -> list[dict[str, Any]]:
    return [l.to_dict() for l in list_labs(lab_type)]


def available_types() -> list[str]:
    return registered_types()
