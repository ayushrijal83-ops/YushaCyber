"""Progress engine — per-session progress tracking.

Provides a unified progress snapshot for any scenario. Works with
the existing ``UserLabSession`` ORM model — no new tables needed.
Every module that wants richer progress reporting calls these
helpers instead of ad-hoc state inspection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.engines.scenario_engine import Scenario, completion_ratio


@dataclass
class Progress:
    """Snapshot of a student's progress through a scenario."""

    scenario_slug: str = ""
    current_objective: dict[str, Any] | None = None
    completed_objectives: list[int] = field(default_factory=list)
    total_objectives: int = 0
    required_objectives: int = 0
    completed_required: int = 0
    ratio: float = 0.0
    hints_used: int = 0
    attempts: int = 0
    completion_time_seconds: int | None = None
    final_score: dict[str, Any] | None = None
    status: str = "not_started"   # not_started | in_progress | completed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_progress(scenario: Scenario,
                     completed_ids: set[int],
                     state: dict[str, Any] | None = None
                     ) -> Progress:
    """Build a progress snapshot from a scenario + session state."""
    state = state or {}
    required = [o for o in scenario.objectives
                if not o.get("is_optional")]
    completed_required = [o for o in required
                          if o.get("id") in completed_ids]

    # Find the first uncompleted required objective as "current".
    current = None
    for obj in scenario.objectives:
        if obj.get("is_optional"):
            continue
        if obj.get("id") not in completed_ids:
            current = obj
            break

    ratio = completion_ratio(scenario, completed_ids)
    if ratio >= 1.0:
        status = "completed"
    elif completed_ids:
        status = "in_progress"
    else:
        status = "not_started"

    return Progress(
        scenario_slug=scenario.slug,
        current_objective=current,
        completed_objectives=sorted(completed_ids),
        total_objectives=len(scenario.objectives),
        required_objectives=len(required),
        completed_required=len(completed_required),
        ratio=round(ratio, 2),
        hints_used=int(state.get("hints_used", 0)),
        attempts=int(state.get("attempts", 0)),
        completion_time_seconds=state.get("completion_time_seconds"),
        final_score=state.get("ir_score") or state.get("final_score"),
        status=status,
    )


def objectives_summary(scenario: Scenario,
                       completed_ids: set[int]) -> list[dict[str, Any]]:
    """Per-objective status list for a progress panel."""
    return [
        {
            "id": obj.get("id"),
            "title": obj.get("title", ""),
            "completed": obj.get("id") in completed_ids,
            "optional": obj.get("is_optional", False),
            "xp": obj.get("xp_reward", 0),
        }
        for obj in scenario.objectives
    ]
