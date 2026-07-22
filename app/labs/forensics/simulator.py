"""Forensics Simulator (YC-029.5.2) — Lab Engine plugin.

Plugs the forensics engine into the existing Simulator contract.
Actions:

  · select      — student clicked an evidence item; state updates so
                  the metadata panel + hash viewer reflect it. Emits
                  ``evidence_inspected`` events used by objectives.
  · flag        — student flagged something as suspicious; emits
                  ``evidence_flagged``.
  · submit      — student submits their findings; evaluated by the
                  engine, emits ``findings_correct`` on success.

Everything is simulated — no real hashing, no filesystem access, no
external tools. The simulator returns pure ActionResults.
"""

from __future__ import annotations

from typing import Any

from app.labs.forensics import engine
from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_INSPECTOR,
    Action,
    ActionResult,
    Simulator,
)


@register_simulator
class ForensicsSimulator(Simulator):
    """Simulated forensic workstation."""

    key = "forensics"

    # ------------------------------------------------------------------
    # Contract
    # ------------------------------------------------------------------
    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        case = (content or {}).get("case") or {}
        return self.new_state_envelope(
            case=case,
            selected=None,
            inspected=[],   # slugs the student has opened
            flagged=[],     # slugs the student has marked suspicious
            findings={},    # last submitted findings dict
            checks={},      # last evaluation result
            findings_correct=False,
        )

    def capabilities(self) -> set[str]:
        return {CAP_INSPECTOR}

    def describe_ui(self) -> dict[str, Any]:
        return {
            "title": "Forensic Workstation — simulated",
            "forensics": True,
        }

    def welcome(self, state: dict[str, Any]) -> str:
        case = state.get("case") or {}
        return (
            "╔══════════════════════════════════════════════════╗\n"
            "║   FORENSIC WORKSTATION — SIMULATED ENVIRONMENT    ║\n"
            "╚══════════════════════════════════════════════════╝\n"
            "\n"
            f"Case: {case.get('title', 'Untitled')}\n"
            f"Workstation: {case.get('workstation_name', 'WORKSTATION-01')}\n"
            f"Investigator: {case.get('investigator', 'You')}\n"
            "\n"
            f"{case.get('briefing', '')}\n"
            "\n"
            "Click an evidence item on the left to inspect metadata and\n"
            "hashes. Study the timeline. Submit your findings when ready."
        )

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        case = state.get("case") or {}
        return [
            {"label": "Case",
             "value": case.get("title") or "—"},
            {"label": "Evidence",
             "value": str(len(case.get("evidence") or []))},
            {"label": "Inspected",
             "value": str(len(state.get("inspected") or []))},
            {"label": "Flagged",
             "value": str(len(state.get("flagged") or []))},
            {"label": "Findings",
             "value": "submitted"
                 if state.get("findings_correct") else "pending",
             "state": "ok" if state.get("findings_correct") else None},
        ]

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------
    def handle(self, state: dict[str, Any],
               action: Action) -> ActionResult:
        state = dict(state)
        case = state.get("case") or {}

        if action.type == "select":
            return self._select(state, case, action)
        if action.type == "flag":
            return self._flag(state, case, action)
        if action.type == "submit":
            return self._submit(state, case, action)

        return ActionResult(
            output="Unknown action. Click an evidence item, flag it, "
                   "or submit findings.",
            new_state=state)

    def _select(self, state: dict[str, Any], case: dict[str, Any],
                action: Action) -> ActionResult:
        slug = str(action.payload.get("asset_id") or "").strip()
        item = engine.find_by_slug(case, slug)
        if item is None:
            return ActionResult(
                output=f"No evidence with id '{slug}'.",
                new_state=state)

        inspected = list(state.get("inspected") or [])
        if slug not in inspected:
            inspected.append(slug)
        state["inspected"] = inspected
        state["selected"] = slug

        metadata = engine.evidence_metadata(item)
        output = (
            f"[SELECTED] {metadata.filename}\n"
            f"  owner:    {metadata.owner}\n"
            f"  created:  {metadata.created}\n"
            f"  modified: {metadata.modified}\n"
            f"  size:     {metadata.size}\n"
            f"  MD5:      {metadata.md5}\n"
            f"  SHA-256:  {metadata.sha256}"
        )
        events = [
            {"type": "evidence_inspected", "asset_id": slug,
             "kind": item.get("kind")},
        ]
        if len(inspected) >= max(1, len(case.get("evidence") or [])):
            events.append({"type": "all_evidence_inspected"})
        return ActionResult(output=output, new_state=state,
                            events=events)

    def _flag(self, state: dict[str, Any], case: dict[str, Any],
              action: Action) -> ActionResult:
        slug = str(action.payload.get("asset_id") or "").strip()
        item = engine.find_by_slug(case, slug)
        if item is None:
            return ActionResult(
                output=f"No evidence with id '{slug}'.",
                new_state=state)

        flagged = list(state.get("flagged") or [])
        if slug in flagged:
            flagged.remove(slug)
            note = "un-flagged"
        else:
            flagged.append(slug)
            note = "flagged as suspicious"
        state["flagged"] = flagged

        events = [{"type": "evidence_flagged", "asset_id": slug,
                   "flagged": slug in flagged}]
        if slug in flagged and item.get("is_suspicious"):
            events.append({"type": "suspicious_flagged", "asset_id": slug})
        return ActionResult(
            output=f"[FLAG] {item['filename']} — {note}.",
            new_state=state, events=events)

    def _submit(self, state: dict[str, Any], case: dict[str, Any],
                action: Action) -> ActionResult:
        payload = action.payload or {}
        findings = {
            "modified_slug": str(payload.get("modified_slug") or ""),
            "modified_hash": str(payload.get("modified_hash") or ""),
            "modified_time": str(payload.get("modified_time") or ""),
            "suspicious_slug": str(payload.get("suspicious_slug") or ""),
        }
        checks = engine.evaluate_findings(case, findings)
        state["findings"] = findings
        state["checks"] = checks
        state["findings_correct"] = bool(checks["all_correct"])

        if checks["all_correct"]:
            output = ("[REPORT] ✅ All findings verified.\n"
                      "Case closed. Well done, investigator.")
            events = [{"type": "findings_correct"}]
        else:
            wrong = [k for k, ok in checks.items()
                     if k != "all_correct" and not ok]
            output = ("[REPORT] ✖ Some findings did not check out: "
                      + ", ".join(wrong) + "\n"
                      "Re-examine the evidence and timeline, then submit "
                      "again.")
            events = [{"type": "findings_incorrect", "wrong": wrong}]
        return ActionResult(output=output, new_state=state, events=events)
