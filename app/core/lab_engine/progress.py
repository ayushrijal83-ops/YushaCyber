"""Lab progress — completion + scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LabProgress:
    lab_slug: str = ""
    user_id: int = 0
    completed_ids: list[str] = field(default_factory=list)
    total_objectives: int = 0
    xp_earned: int = 0
    hints_used: int = 0
    attempts: int = 0
    started: bool = False
    completed: bool = False

    @property
    def pct(self) -> float:
        if self.total_objectives <= 0:
            return 0.0
        return round(len(self.completed_ids) /
                     self.total_objectives, 2)

    def complete(self, objective_id: str, xp: int = 0) -> bool:
        if objective_id in self.completed_ids:
            return False
        self.completed_ids.append(objective_id)
        self.xp_earned += xp
        if len(self.completed_ids) >= self.total_objectives:
            self.completed = True
        return True

    def use_hint(self) -> None:
        self.hints_used += 1

    def add_attempt(self) -> None:
        self.attempts += 1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pct"] = self.pct
        return d
