"""Conversation memory — per-session message history.

No permanent storage — conversation resets each session.
Memory is keyed by user_id and stored in a module-level dict.
"""

from __future__ import annotations

from app.core.ai.types import Message

MAX_HISTORY = 20  # messages per conversation

_conversations: dict[int, list[Message]] = {}


def get_history(user_id: int) -> list[Message]:
    """Get conversation history for a user."""
    return list(_conversations.get(user_id, []))


def add_message(user_id: int, message: Message) -> None:
    """Append a message and trim to MAX_HISTORY."""
    if user_id not in _conversations:
        _conversations[user_id] = []
    _conversations[user_id].append(message)
    if len(_conversations[user_id]) > MAX_HISTORY:
        _conversations[user_id] = _conversations[user_id][-MAX_HISTORY:]


def clear(user_id: int) -> None:
    """Clear conversation history."""
    _conversations.pop(user_id, None)


def clear_all() -> None:
    """Clear all conversations (admin)."""
    _conversations.clear()
