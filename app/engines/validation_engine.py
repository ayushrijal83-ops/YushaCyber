"""Validation engine — generic validator with extended types.

Wraps the existing ``app/labs/validator.py`` registry and adds new
validator types that every module can use. All existing validators
(``exact_command``, ``regex_command``, ``output_contains``,
``state_flag``, ``event_emitted``) keep working unchanged.

New validators registered here:
  · ``exact_match``      — string-equal (case-insensitive) answer check
  · ``multi_step``       — all listed events must have fired
  · ``ordered_tasks``    — events must fire in the given order
  · ``score_threshold``  — a numeric state value must meet a minimum
  · ``custom_hook``      — delegates to a named function

These are registered into the *same* global registry that
``app/labs/validator.py`` uses, so ``LabObjective`` rows can
reference them via ``validator_type`` without any code change
in the action pipeline.
"""

from __future__ import annotations

from typing import Any

from app.labs.validator import ValidationContext, register_validator


# ---------------------------------------------------------------------------
# New generic validators
# ---------------------------------------------------------------------------

@register_validator("exact_match")
def _exact_match(spec: dict, ctx: ValidationContext) -> bool:
    """Case-insensitive string comparison of a state value against
    an expected answer.

    spec: {"path": "findings.suspicious_ip", "expected": "203.0.113.50"}
    """
    path = spec.get("path")
    expected = str(spec.get("expected") or "").strip().lower()
    if not path or not expected:
        return False
    actual = str(ctx.state_value(path) or "").strip().lower()
    return actual == expected


@register_validator("multi_step")
def _multi_step(spec: dict, ctx: ValidationContext) -> bool:
    """Every listed event must have fired at least once across the
    session's event history.

    spec: {"events": ["source_opened", "artifact_inspected",
                      "findings_correct"]}
    """
    required = spec.get("events") or []
    if not required:
        return True
    fired = {e.get("type") for e in ctx.events}
    return all(ev in fired for ev in required)


@register_validator("ordered_tasks")
def _ordered_tasks(spec: dict, ctx: ValidationContext) -> bool:
    """Events must appear in the given order (not necessarily
    consecutively) in the session's event log.

    spec: {"events": ["alert_opened", "evidence_inspected",
                      "findings_correct"]}
    """
    required = spec.get("events") or []
    if not required:
        return True
    event_sequence = [e.get("type") for e in ctx.events]
    idx = 0
    for event_type in event_sequence:
        if idx < len(required) and event_type == required[idx]:
            idx += 1
    return idx >= len(required)


@register_validator("score_threshold")
def _score_threshold(spec: dict, ctx: ValidationContext) -> bool:
    """A numeric state value must meet or exceed a minimum.

    spec: {"path": "ir_score.total", "min": 50}
    """
    path = spec.get("path")
    minimum = spec.get("min", 0)
    if not path:
        return False
    value = ctx.state_value(path)
    try:
        return float(value) >= float(minimum)
    except (TypeError, ValueError):
        return False


@register_validator("custom_hook")
def _custom_hook(spec: dict, ctx: ValidationContext) -> bool:
    """Delegates to a named Python function.

    spec: {"function": "app.engines.my_module.my_check",
           "args": {"key": "value"}}

    The function receives (spec, ctx) and returns bool. If the
    function can't be imported, returns False (safe failure).
    """
    func_path = spec.get("function") or ""
    if not func_path:
        return False
    try:
        parts = func_path.rsplit(".", 1)
        if len(parts) != 2:
            return False
        module_path, func_name = parts
        import importlib
        mod = importlib.import_module(module_path)
        func = getattr(mod, func_name)
        return bool(func(spec, ctx))
    except (ImportError, AttributeError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Utility — check a single spec against a context (useful outside
# the action pipeline, e.g. for manual grading in seed scripts).
# ---------------------------------------------------------------------------
def validate(validator_type: str,
             validator_data: dict[str, Any],
             ctx: ValidationContext) -> bool:
    """Run one validator by name, returning True/False."""
    from app.labs.validator import VALIDATOR_REGISTRY
    func = VALIDATOR_REGISTRY.get(validator_type)
    if func is None:
        return False
    return func(validator_data, ctx)
