"""Incident Response workflow engine (YC-030.3).

Models the five NIST IR phases as a linear gate: the student must
complete each phase before advancing. Each phase has a set of
expected correct actions (from the decision engine) and a
completion condition.

Reusable: a new IR scenario just seeds a different ``IR_SCENARIO``
dict with its own actions-per-phase + case link.
"""

from __future__ import annotations

from typing import Any

from app.simulators.soc.models import PLAYBOOK_PHASES

#: Canonical phase ordering (same as playbook phases).
IR_PHASES = list(PLAYBOOK_PHASES)

PHASE_LABELS = {
    "identification": "Identification",
    "containment": "Containment",
    "eradication": "Eradication",
    "recovery": "Recovery",
    "lessons_learned": "Lessons Learned",
}


def current_phase(completed: list[str]) -> str | None:
    """Return the phase the student should work on next, or None
    if all phases are done."""
    for phase in IR_PHASES:
        if phase not in completed:
            return phase
    return None


def can_advance(phase: str, completed: list[str]) -> bool:
    """True if the student is allowed to enter ``phase``."""
    idx = IR_PHASES.index(phase) if phase in IR_PHASES else 999
    # Must have completed every prior phase.
    for p in IR_PHASES[:idx]:
        if p not in completed:
            return False
    return True


def phase_status(completed: list[str]) -> list[dict[str, Any]]:
    """Build the phase-progress display for the UI."""
    cur = current_phase(completed)
    return [
        {
            "phase": p,
            "label": PHASE_LABELS.get(p, p),
            "completed": p in completed,
            "current": p == cur,
            "locked": not can_advance(p, completed),
        }
        for p in IR_PHASES
    ]


def all_phases_complete(completed: list[str]) -> bool:
    return set(IR_PHASES).issubset(set(completed))
