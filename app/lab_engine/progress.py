"""Lab progress — objective completion tracking."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LabProgress:
    lab_slug: str = ""
    user_id: int = 0
    completed_objectives: list[str] = field(default_factory=list)
    total_objectives: int = 0
    xp_earned: int = 0
    started: bool = False
    completed: bool = False

    @property
    def pct(self) -> float:
        if self.total_objectives <= 0:
            return 0.0
        return round(len(self.completed_objectives) /
                     self.total_objectives, 2)

    def complete_objective(self, obj_id: str, xp: int = 0) -> bool:
        if obj_id in self.completed_objectives:
            return False
        self.completed_objectives.append(obj_id)
        self.xp_earned += xp
        if len(self.completed_objectives) >= self.total_objectives:
            self.completed = True
        return True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pct"] = self.pct
        return d
