"""CyberMentor — the high-level mentor interface.

Combines context, prompts, memory, and the AI manager into one
simple API: ``mentor.ask(user, question)``.
"""

from __future__ import annotations

from typing import Any

from app.core.ai import memory
from app.core.ai.manager import get_manager
from app.core.ai.prompts import build_system_message
from app.core.ai.types import ChatResponse, MentorContext, Message


def ask(user, question: str,
        current_lab: str = "",
        current_scenario: str = "",
        **kwargs: Any) -> ChatResponse:
    """Ask CyberMentor a question with full student context."""
    # Use the intelligent context engine (YC-032.2).
    from app.core.ai.context_engine import get_context
    full_ctx = get_context(user, current_lab, current_scenario)
    # Convert to MentorContext for backward compat.
    ctx = MentorContext(
        username=full_ctx.user.username,
        level=full_ctx.progress.level,
        xp=full_ctx.progress.xp,
        completed_labs=[],
        current_lab=full_ctx.learning.current_lab,
        current_scenario=full_ctx.learning.current_scenario,
        current_difficulty=full_ctx.learning.difficulty,
        achievements=[a for a in full_ctx.achievements.recent_achievements],
        certificates=full_ctx.achievements.certificates,
    )
    return ask_with_context(ctx, user.id, question, **kwargs)


def ask_with_context(context: MentorContext, user_id: int,
                     question: str,
                     **kwargs: Any) -> ChatResponse:
    """Ask with a pre-built context (for testing)."""
    # Build message list: system + history + new question.
    system_msg = build_system_message(context)
    history = memory.get_history(user_id)
    user_msg = Message(role="user", content=question)

    messages = [system_msg] + history + [user_msg]

    # Call the AI manager.
    manager = get_manager()
    response = manager.chat(messages, **kwargs)

    # Save to conversation memory.
    memory.add_message(user_id, user_msg)
    memory.add_message(user_id,
                       Message(role="assistant",
                               content=response.content))
    return response
