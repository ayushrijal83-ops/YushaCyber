"""Playbook helpers.

Turns a ``SocPlaybook`` and its steps into the shape the UI renders —
one bucket per IR-lifecycle phase, in the canonical order.
"""

from __future__ import annotations

from typing import Any

from app.simulators.soc.models import PLAYBOOK_PHASES, SocPlaybook


PHASE_LABEL = {
    "identification":   "Identification",
    "containment":      "Containment",
    "eradication":      "Eradication",
    "recovery":         "Recovery",
    "lessons_learned":  "Lessons Learned",
}


def playbook_view(playbook: SocPlaybook | None) -> dict[str, Any]:
    """Grouped-by-phase view of the playbook, or an empty scaffold."""
    if playbook is None:
        return {"title": "", "alert_type": "", "summary": "",
                "phases": []}
    grouped: dict[str, list[dict[str, Any]]] = {p: [] for p in PLAYBOOK_PHASES}
    for step in playbook.steps:
        grouped.setdefault(step.phase, []).append({
            "title": step.title, "body": step.body,
            "display_order": step.display_order,
        })
    return {
        "title": playbook.title,
        "alert_type": playbook.alert_type,
        "summary": playbook.summary,
        "phases": [
            {"key": phase, "label": PHASE_LABEL[phase],
             "steps": grouped[phase]}
            for phase in PLAYBOOK_PHASES
        ],
    }
