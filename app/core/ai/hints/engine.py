"""Hint engine — orchestrates the full hint flow."""

from __future__ import annotations

from app.core.ai.hints import history, rules
from app.core.ai.hints.generator import generate
from app.core.ai.hints.models import HintConfig, HintResponse

_CONFIG = HintConfig()


def get_config() -> HintConfig:
    return _CONFIG


def set_config(config: HintConfig) -> None:
    global _CONFIG
    _CONFIG = config


def request_hint(user_id: int, objective_id: int,
                 is_admin: bool = False) -> HintResponse:
    """Main entry point — request a hint for an objective.

    Handles rate limiting, level progression, generation,
    history recording, and XP penalty computation.
    """
    config = get_config()

    # Validate.
    error = rules.validate_request(objective_id, user_id)
    if error:
        return HintResponse(hint=error, level=0)

    # Rate limit.
    if rules.check_rate_limit(user_id, config):
        return HintResponse(
            hint="Please wait before requesting another hint.",
            rate_limited=True, level=0)

    # Determine level.
    current = history.current_level(user_id, objective_id)
    level = rules.next_level(current, is_admin, config)
    remaining = rules.remaining_levels(level, is_admin)

    # Get the objective from DB.
    try:
        from app.labs.models import LabObjective
        objective = LabObjective.query.get(objective_id)
        if objective is None:
            return HintResponse(hint="Objective not found.", level=0)
    except Exception:
        return HintResponse(hint="Could not load objective.", level=0)

    # Get lab info.
    lab_title = ""
    difficulty = ""
    try:
        if objective.lab:
            lab_title = objective.lab.title
            difficulty = objective.lab.difficulty
    except Exception:
        pass

    # Previous hints for context.
    prev_records = history.get_history(user_id, objective_id)
    previous_hints = [r.lab_slug for r in prev_records]  # placeholder

    # Generate.
    response = generate(
        objective, level, previous_hints,
        lab_title, difficulty,
        attempts=len(prev_records))
    response.remaining_levels = remaining
    response.xp_penalty = config.penalty_for(level)

    # Record.
    lab_slug = ""
    try:
        lab_slug = objective.lab.slug if objective.lab else ""
    except Exception:
        pass
    history.record(user_id, objective_id, lab_slug, level)

    return response
