"""Context engine services — the public API."""

from __future__ import annotations

from typing import Any

from app.core.ai.context_engine.builder import build
from app.core.ai.context_engine.models import FullContext
from app.core.ai.context_engine.progress import LearningProfile, analyze


def get_context(user, current_lab: str = "",
                current_scenario: str = "",
                current_objective: str = "") -> FullContext:
    """Build the full enriched context for an AI request."""
    return build(user, current_lab, current_scenario,
                 current_objective)


def get_context_dict(user, **kwargs: Any) -> dict[str, Any]:
    """Same as get_context but returns a dict."""
    return get_context(user, **kwargs).to_dict()


def get_context_summary(user, **kwargs: Any) -> str:
    """Human-readable summary for the system prompt."""
    return get_context(user, **kwargs).summary_text()


def get_learning_profile(user) -> LearningProfile:
    """Analyze the student's learning profile."""
    return analyze(user)


def filter_for_ai(context: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive fields before sending to the AI provider."""
    safe = dict(context)
    # Remove any keys that might leak.
    for key in ("api_key", "password", "secret", "token",
                "correct_answer", "solution", "instructor_notes"):
        safe.pop(key, None)
    # Recursively filter nested dicts.
    for k, v in safe.items():
        if isinstance(v, dict):
            safe[k] = filter_for_ai(v)
    return safe
