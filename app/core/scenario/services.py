"""Scenario services — the public API.

Every interactive learning module calls these functions instead of
reaching into the ORM directly. The services bridge the new
Scenario dataclasses and the existing Lab / LabObjective / session
manager / achievement / certificate infrastructure.
"""

from __future__ import annotations

from typing import Any

from app.core.scenario.models import (
    Scenario,
    scenario_from_dict,
    scenario_from_lab,
)
from app.core.scenario.progress import Progress
from app.core.scenario import progress as progress_mod, validator


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load_scenario(lab_or_dict) -> Scenario:
    """Load a Scenario from an ORM Lab or a plain dict.

    Usage:
        scenario = load_scenario(lab)          # from ORM
        scenario = load_scenario({"slug": …})  # from dict
    """
    if isinstance(lab_or_dict, dict):
        return scenario_from_dict(lab_or_dict)
    return scenario_from_lab(lab_or_dict)


# ---------------------------------------------------------------------------
# Objectives
# ---------------------------------------------------------------------------
def complete_objective(user, lab, objective_id: int) -> dict[str, Any]:
    """Mark an objective as completed for a user. Awards XP.

    Delegates to the existing ``lab_services`` so achievements,
    certificates and XP all fire through the same pipeline.
    """
    from app.labs.models import UserObjectiveProgress
    from app.extensions import db

    row = UserObjectiveProgress.query.filter_by(
        user_id=user.id, objective_id=objective_id).first()
    if row is None:
        row = UserObjectiveProgress(
            user_id=user.id, objective_id=objective_id)
        db.session.add(row)
    if row.completed:
        return {"ok": True, "already_completed": True, "xp": 0}
    row.completed = True
    db.session.flush()

    from app.labs.models import LabObjective
    objective = LabObjective.query.get(objective_id)
    xp = 0
    if objective and objective.xp_reward:
        from app.dashboard.services import award_xp as _award
        _award(user, objective.xp_reward)
        xp = objective.xp_reward
    return {"ok": True, "already_completed": False, "xp": xp}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_submission(scenario: Scenario,
                        state: dict[str, Any],
                        events: list[dict[str, Any]] | None = None
                        ) -> dict[str, bool]:
    """Validate the scenario's global validation rules."""
    return validator.validate_all(
        scenario.validation_rules, state, events)


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------
def calculate_progress(scenario: Scenario,
                       completed_ids: set[int],
                       state: dict[str, Any] | None = None
                       ) -> Progress:
    """Compute a progress snapshot."""
    return progress_mod.calculate(scenario, completed_ids, state)


# ---------------------------------------------------------------------------
# XP
# ---------------------------------------------------------------------------
def award_xp(user, amount: int) -> int:
    """Award XP to a user. Returns new total."""
    from app.dashboard.services import award_xp as _award
    _award(user, amount)
    return user.xp


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def generate_report(scenario: Scenario,
                    progress: Progress,
                    state: dict[str, Any] | None = None
                    ) -> dict[str, Any]:
    """Generate a completion report dict for any scenario.

    The report is a structured summary — not the student's written
    report. It's used by the completion modal, certificate engine
    and leaderboard.
    """
    state = state or {}
    return {
        "scenario": {
            "slug": scenario.slug,
            "title": scenario.title,
            "difficulty": scenario.difficulty,
            "category": scenario.category,
        },
        "progress": progress.to_dict(),
        "score": {
            "total": progress.score,
            "max": progress.max_score,
            "grade": progress.grade,
            "ratio": progress.ratio,
        },
        "xp_earned": sum(
            o.xp_reward for o in scenario.objectives
            if o.id in set(progress.completed_objectives)
        ) + (scenario.xp_reward
             if progress.is_complete else 0),
        "hints_used": progress.hints_used,
        "completion_seconds": progress.completion_seconds,
        "report_type": scenario.report_type,
    }
