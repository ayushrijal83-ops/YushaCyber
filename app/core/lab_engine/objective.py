"""Lab objectives — universal tracking + validation bridge.

Reuses the existing validation engine from app/engines/.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.lab_engine.types import LabObjectiveDef


@dataclass
class ObjectiveResult:
    passed: bool = False
    objective_id: str = ""
    message: str = ""
    xp_earned: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "objective_id": self.objective_id,
                "message": self.message, "xp_earned": self.xp_earned}


def check(objective: LabObjectiveDef,
          submission: str = "",
          context: dict[str, Any] | None = None) -> ObjectiveResult:
    """Validate a submission against an objective.

    Routes to the right check based on objective.kind.
    """
    expected = (objective.expected or "").strip().lower()
    given = submission.strip().lower()

    if not expected:
        return ObjectiveResult(objective_id=objective.id,
                               message="No validation rule.")

    if objective.kind == "capture_flag":
        if given == expected:
            return _pass(objective)
        return ObjectiveResult(objective_id=objective.id,
                               message="Incorrect flag.")

    if objective.kind == "answer_question":
        if given == expected or expected in given:
            return _pass(objective)
        return ObjectiveResult(objective_id=objective.id,
                               message="Not quite right.")

    # Default: substring match (run_command, read_file, etc.)
    if given == expected or expected in given:
        return _pass(objective)

    return ObjectiveResult(objective_id=objective.id,
                           message="Try again.")


def _pass(obj: LabObjectiveDef,
          msg: str = "Objective completed!") -> ObjectiveResult:
    return ObjectiveResult(passed=True, objective_id=obj.id,
                           message=msg, xp_earned=obj.xp)
