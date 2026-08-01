"""AI models — conversation tracking (in-memory)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.ai.types import Message


@dataclass
class Conversation:
    """One conversation session."""
    user_id: int = 0
    messages: list[Message] = field(default_factory=list)
    lab_context: str = ""
    started_at: str = ""

    def add(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "messages": [m.to_dict() for m in self.messages],
            "lab_context": self.lab_context,
            "message_count": len(self.messages),
        }
