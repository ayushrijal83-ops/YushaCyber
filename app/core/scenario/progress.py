"""Progress tracking for any scenario."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.scenario.models import Scenario
from app.core.scenario.types import Grade


@dataclass
class Progress:
    """Snapshot of a student's progress through a scenario."""

    scenario_slug: str = ""
    current_objective_id: int | None = None
    current_objective_title: str = ""
    completed_objectives: list[int] = field(default_factory=list)
    total_objectives: int = 0
    required_objectives: int = 0
    completed_required: int = 0
    ratio: float = 0.0
    hints_used: int = 0
    attempts: int = 0
    start_time: str | None = None
    completion_time: str | None = None
    completion_seconds: int | None = None
    score: int = 0
    max_score: int = 0
    grade: str = Grade.FAIL.value
    status: str = "not_started"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"


def calculate(scenario: Scenario,
              completed_ids: set[int],
              state: dict[str, Any] | None = None) -> Progress:
    """Build a progress snapshot."""
    state = state or {}
    required = scenario.required_objectives
    done_required = [o for o in required
                     if o.id in completed_ids]

    current = None
    for obj in scenario.objectives:
        if obj.is_optional:
            continue
        if obj.id not in completed_ids:
            current = obj
            break

    total = len(scenario.objectives)
    n_required = len(required)
    n_done = len(done_required)
    ratio = n_done / max(1, n_required)

    if ratio >= 1.0:
        status = "completed"
    elif completed_ids:
        status = "in_progress"
    else:
        status = "not_started"

    score = state.get("score") or state.get("assessment_score", {})
    if isinstance(score, dict):
        grade_str = score.get("grade") or score.get("rating", "")
        score_val = score.get("total", 0)
        max_val = score.get("max", 0)
    else:
        grade_str = ""
        score_val = int(score or 0)
        max_val = 0

    return Progress(
        scenario_slug=scenario.slug,
        current_objective_id=current.id if current else None,
        current_objective_title=current.title if current else "",
        completed_objectives=sorted(completed_ids),
        total_objectives=total,
        required_objectives=n_required,
        completed_required=n_done,
        ratio=round(ratio, 2),
        hints_used=int(state.get("hints_used", 0)),
        attempts=int(state.get("attempts", 0)),
        start_time=state.get("start_time"),
        completion_time=state.get("completion_time"),
        completion_seconds=state.get("completion_seconds"),
        score=score_val,
        max_score=max_val,
        grade=grade_str or Grade.FAIL.value,
        status=status,
    )


def objectives_summary(scenario: Scenario,
                       completed_ids: set[int]
                       ) -> list[dict[str, Any]]:
    """Per-objective status list."""
    return [
        {
            "id": obj.id,
            "title": obj.title,
            "completed": obj.id in completed_ids,
            "optional": obj.is_optional,
            "xp": obj.xp_reward,
            "type": obj.objective_type,
        }
        for obj in scenario.objectives
    ]
