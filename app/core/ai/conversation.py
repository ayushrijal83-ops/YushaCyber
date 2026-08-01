"""Conversation session management."""

from __future__ import annotations

from app.core.ai import memory
from app.core.ai.models import Conversation


def get_conversation(user_id: int) -> Conversation:
    """Get or create a conversation for a user."""
    history = memory.get_history(user_id)
    return Conversation(user_id=user_id, messages=history)


def reset_conversation(user_id: int) -> None:
    """Clear conversation history."""
    memory.clear(user_id)
