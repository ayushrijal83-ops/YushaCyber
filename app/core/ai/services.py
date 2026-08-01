"""AI services — the public API for CyberMentor."""

from __future__ import annotations

from typing import Any

from app.core.ai.config import is_enabled
from app.core.ai.context import context_from_dict
from app.core.ai.manager import get_manager
from app.core.ai.mentor import ask, ask_with_context
from app.core.ai.providers import (
    PROVIDERS,
)


def chat(user_id: int, question: str,
         user=None, current_lab: str = "",
         **kwargs: Any) -> dict[str, Any]:
    """Public chat endpoint — returns a dict."""
    if not is_enabled():
        return {"content": "AI mentor is currently disabled.",
                "provider": "none", "error": False}
    if user is not None:
        response = ask(user, question, current_lab, **kwargs)
    else:
        ctx = context_from_dict({"username": f"user_{user_id}",
                                 "level": 1, "xp": 0})
        response = ask_with_context(ctx, user_id, question, **kwargs)
    return response.to_dict()


def health() -> dict[str, Any]:
    """Health check."""
    if not is_enabled():
        return {"status": "disabled"}
    return get_manager().health()


def models() -> list[str]:
    """List available models."""
    return get_manager().models()


def usage() -> dict[str, Any]:
    """Usage statistics."""
    return get_manager().usage().to_dict()


def available_providers() -> list[str]:
    """List registered providers."""
    return sorted(PROVIDERS.keys())
