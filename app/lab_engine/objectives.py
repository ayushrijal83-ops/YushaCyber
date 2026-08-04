"""Lab objectives — task definitions + completion tracking."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Objective:
    id: str = ""
    title: str = ""
    description: str = ""
    hint: str = ""
    validation_type: str = "command"  # command | file | answer | sequence
    expected: str = ""                # expected command/answer/file
    xp: int = 50
    completed: bool = False
    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LabDefinition:
    """A complete lab scenario."""
    slug: str = ""
    title: str = ""
    description: str = ""
    mode: str = "linux"
    difficulty: str = "Easy"
    category: str = "general"
    xp_total: int = 100
    objectives: list[Objective] = field(default_factory=list)
    filesystem: dict[str, Any] | None = None
    intro_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug, "title": self.title,
            "description": self.description,
            "mode": self.mode, "difficulty": self.difficulty,
            "category": self.category, "xp_total": self.xp_total,
            "intro_text": self.intro_text,
            "objectives": [o.to_dict() for o in self.objectives],
        }
