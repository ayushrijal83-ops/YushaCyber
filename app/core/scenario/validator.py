"""Scenario validator — clean API over the existing registry.

Every validator registered in ``app/labs/validator.py`` and
``app/engines/validation_engine.py`` is available here. This
module adds no new validators — it provides a unified interface.
"""

from __future__ import annotations

from typing import Any

from app.core.scenario.types import ValidationRule
from app.labs.simulator_base import Action
from app.labs.validator import VALIDATOR_REGISTRY, ValidationContext


def validate(rule: ValidationRule,
             state: dict[str, Any],
             events: list[dict[str, Any]] | None = None,
             action: Action | None = None) -> bool:
    """Run one validation rule against state + events."""
    func = VALIDATOR_REGISTRY.get(rule.validator_type)
    if func is None:
        return False
    ctx = ValidationContext(
        action=action or Action(type="check", payload={}),
        state=state,
        events=events or [])
    return func(rule.data, ctx)


def validate_all(rules: list[ValidationRule],
                 state: dict[str, Any],
                 events: list[dict[str, Any]] | None = None
                 ) -> dict[str, bool]:
    """Run every rule, returning {validator_type: bool}."""
    return {
        rule.validator_type: validate(rule, state, events)
        for rule in rules
    }


def available_validators() -> list[str]:
    """List all registered validator names."""
    return sorted(VALIDATOR_REGISTRY.keys())
