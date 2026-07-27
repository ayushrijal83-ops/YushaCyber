"""Scenario engine — lifecycle helpers.

Stateless functions that operate on Scenario + Progress dataclasses.
No ORM, no side effects — pure logic.
"""

from __future__ import annotations


from app.core.scenario.models import Scenario
from app.core.scenario.types import Grade


def is_complete(scenario: Scenario,
                completed_ids: set[int]) -> bool:
    """True when every required objective is done."""
    return all(o.id in completed_ids
               for o in scenario.required_objectives)


def completion_ratio(scenario: Scenario,
                     completed_ids: set[int]) -> float:
    required = scenario.required_objectives
    if not required:
        return 1.0
    return sum(1 for o in required
               if o.id in completed_ids) / len(required)


def compute_grade(ratio: float, score_ratio: float = 0.0) -> str:
    """Determine the final grade from completion + score ratios."""
    combined = (ratio * 0.6) + (score_ratio * 0.4)
    if combined >= 0.90:
        return Grade.EXCELLENT.value
    if combined >= 0.75:
        return Grade.GOOD.value
    if combined >= 0.60:
        return Grade.PASS.value
    if combined >= 0.40:
        return Grade.NEEDS_IMPROVEMENT.value
    return Grade.FAIL.value


def next_objective(scenario: Scenario,
                   completed_ids: set[int]) -> int | None:
    """Return the id of the next uncompleted required objective."""
    for obj in scenario.objectives:
        if obj.is_optional:
            continue
        if obj.id not in completed_ids:
            return obj.id
    return None


def total_xp_available(scenario: Scenario) -> int:
    """Sum of lab XP + all objective XP."""
    return scenario.total_xp
