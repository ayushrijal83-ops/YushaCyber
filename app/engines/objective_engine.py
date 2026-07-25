"""Objective engine — reusable objective types and helpers.

Provides a type registry and builder functions so every module
(Forensics, SOC, Networking, future AD/Cloud/API) creates
objectives the same way. Backward-compatible: existing
``LabObjective`` rows work unchanged because the validator types
they reference (``exact_command``, ``state_flag``,
``event_emitted``) are still registered in ``app/labs/validator.py``.

This module adds higher-level *objective type* helpers on top of
the raw validator interface — they produce the same
``(validator_type, validator_data)`` tuples but give seed code a
semantic API instead of raw dicts.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Objective type builders — each returns a (validator_type, validator_data)
# pair ready to write into LabObjective.
# ---------------------------------------------------------------------------

def visit_panel(panel_name: str) -> tuple[str, dict[str, Any]]:
    """Student must open / visit a named panel (emits an event)."""
    return ("event_emitted", {"event": f"{panel_name}_visited"})


def inspect_evidence(event: str = "all_evidence_inspected"
                     ) -> tuple[str, dict[str, Any]]:
    """Student must inspect every evidence item."""
    return ("event_emitted", {"event": event})


def execute_command(command: str) -> tuple[str, dict[str, Any]]:
    """Student must run a specific simulated command."""
    return ("exact_command", {"command": command})


def answer_question(path: str,
                    expected: Any) -> tuple[str, dict[str, Any]]:
    """Student must set a state value to the expected answer."""
    return ("state_flag", {"path": path, "equals": expected})


def submit_report(event: str = "findings_correct"
                  ) -> tuple[str, dict[str, Any]]:
    """Student must submit a report that passes validation."""
    return ("event_emitted", {"event": event})


def complete_timeline(event: str = "all_sources_opened"
                      ) -> tuple[str, dict[str, Any]]:
    """Student must review / complete the full timeline."""
    return ("event_emitted", {"event": event})


def identify_root_cause(path: str = "checks.root_cause",
                        expected: bool = True
                        ) -> tuple[str, dict[str, Any]]:
    """Student must correctly identify the root cause."""
    return ("state_flag", {"path": path, "equals": expected})


def score_threshold(path: str = "ir_score.rating",
                    expected: str = "Good"
                    ) -> tuple[str, dict[str, Any]]:
    """Score-based completion — e.g. IR score must be Good+."""
    return ("state_flag", {"path": path, "equals": expected})


def multi_step(events: list[str]) -> list[tuple[str, dict[str, Any]]]:
    """Return a list of objectives that must fire in sequence.

    Each element is an (event_emitted, {...}) pair. The caller seeds
    one LabObjective per step.
    """
    return [("event_emitted", {"event": e}) for e in events]


def custom_hook(hook_name: str,
                data: dict[str, Any] | None = None
                ) -> tuple[str, dict[str, Any]]:
    """Escape hatch: reference a custom validator registered in
    ``app/labs/validator.py`` via ``@register_validator``."""
    return (hook_name, data or {})


# ---------------------------------------------------------------------------
# Objective dict builder (convenience for seed code)
# ---------------------------------------------------------------------------
def build_objective(
        title: str,
        instruction: str,
        objective_type: tuple[str, dict[str, Any]],
        xp: int = 10,
        order: int = 1,
        hints: list[str] | None = None,
        optional: bool = False) -> dict[str, Any]:
    """Return a dict ready to pass to ``LabObjective`` constructor
    or ``set_validator_data``."""
    validator_type, validator_data = objective_type
    return {
        "title": title,
        "instruction": instruction,
        "description": instruction,
        "validator_type": validator_type,
        "validator_data": validator_data,
        "xp_reward": xp,
        "display_order": order,
        "is_optional": optional,
        "hint1": hints[0] if hints and len(hints) > 0 else None,
        "hint2": hints[1] if hints and len(hints) > 1 else None,
        "hint3": hints[2] if hints and len(hints) > 2 else None,
    }
