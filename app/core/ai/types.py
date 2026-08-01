"""AI types — provider interface, config, message types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: str = "user"
    content: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatResponse:
    content: str = ""
    model: str = ""
    provider: str = ""
    tokens_used: int = 0
    finish_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AIConfig:
    """Provider-agnostic configuration."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    timeout: int = 30
    max_tokens: int = 1024
    temperature: float = 0.7
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "AIConfig":
        import os
        return cls(
            provider=os.environ.get("AI_PROVIDER", "openai"),
            model=os.environ.get("AI_MODEL", "gpt-4o-mini"),
            api_key=os.environ.get("AI_API_KEY", ""),
            base_url=os.environ.get("AI_BASE_URL", ""),
            timeout=int(os.environ.get("AI_TIMEOUT", "30")),
            max_tokens=int(os.environ.get("AI_MAX_TOKENS", "1024")),
            enabled=os.environ.get("AI_ENABLED", "true").lower() == "true",
        )


@dataclass
class MentorContext:
    """Everything the mentor knows about the current student."""
    username: str = ""
    level: int = 1
    xp: int = 0
    completed_tracks: list[str] = field(default_factory=list)
    completed_labs: list[str] = field(default_factory=list)
    current_lab: str = ""
    current_scenario: str = ""
    current_difficulty: str = ""
    achievements: list[str] = field(default_factory=list)
    certificates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        parts = [f"Student: {self.username}",
                 f"Level {self.level} ({self.xp} XP)"]
        if self.completed_labs:
            parts.append(f"Completed {len(self.completed_labs)} labs")
        if self.current_lab:
            parts.append(f"Currently on: {self.current_lab}")
        if self.current_difficulty:
            parts.append(f"Difficulty: {self.current_difficulty}")
        if self.achievements:
            parts.append(f"{len(self.achievements)} achievements")
        if self.certificates:
            parts.append(f"{len(self.certificates)} certificates")
        return ". ".join(parts) + "."


@dataclass
class UsageStats:
    """Token usage tracking."""
    total_requests: int = 0
    total_tokens: int = 0
    failed_requests: int = 0
    provider: str = ""
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
