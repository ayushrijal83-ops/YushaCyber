"""Hint models — levels, history, request/response types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


HINT_LEVELS = (1, 2, 3, 4)  # 4 = admin-only solution reveal
MAX_STUDENT_LEVEL = 3


@dataclass
class HintConfig:
    """Per-deployment hint policy."""
    penalties: dict[int, int] = field(default_factory=lambda: {
        1: 0, 2: 5, 3: 10, 4: 0})
    rate_limit_seconds: int = 15
    allow_level_4: bool = False  # admin toggle

    def penalty_for(self, level: int) -> int:
        return self.penalties.get(level, 0)


@dataclass
class HintRequest:
    user_id: int = 0
    objective_id: int = 0
    lab_slug: str = ""
    current_level: int = 0  # already-used level
    attempts: int = 0
    time_spent_seconds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HintResponse:
    level: int = 1
    hint: str = ""
    remaining_levels: int = 2
    xp_penalty: int = 0
    source: str = "static"  # static | ai | generic
    rate_limited: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HintRecord:
    """One entry in the hint history."""
    user_id: int = 0
    objective_id: int = 0
    lab_slug: str = ""
    level: int = 1
    timestamp: float = 0.0
    solved_after: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HintStats:
    """Analytics for hints."""
    total_requests: int = 0
    avg_hints_per_objective: float = 0.0
    avg_level: float = 0.0
    most_requested_objectives: list[dict[str, Any]] = field(
        default_factory=list)
    hint_success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
