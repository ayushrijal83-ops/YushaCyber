"""SOC Analyst simulator plugin.

Wraps the forensics simulator with a SOC-specific triage envelope:

  · The lab loads with an alert queue (the dashboard); no case is
    active yet.
  · ``open_alert`` picks one — from there every forensics action
    (``select_source``, ``select_artifact``, ``link_artifacts``,
    ``select_suspect``) works exactly as it would in a forensics lab.
  · SOC-specific actions add on top: ``tick_checklist``,
    ``select_playbook``, ``set_root_cause``, ``close_incident``.

Nothing about forensics is reimplemented — the SOC simulator delegates
the forensics actions to the existing plugin instance and just
maintains a superset of state on top.
"""

from __future__ import annotations

from typing import Any

from app.labs.forensics.simulator import ForensicsSimulator
from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_INSPECTOR,
    Action,
    ActionResult,
    Simulator,
)
from app.simulators.soc import report_engine, services


@register_simulator
class SOCSimulator(Simulator):
    """The SOC analyst workspace."""

    key = "soc"

    def __init__(self) -> None:
        # Compose — do not inherit. The forensics simulator carries its
        # own bootstrap/handle contract; we forward actions to it.
        self._forensics = ForensicsSimulator()

    # ------------------------------------------------------------------
    # Contract
    # ------------------------------------------------------------------
    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        """Load the SOC dashboard state — no alert active yet.

        ``content`` is expected to include a ``soc_lab`` marker + a
        ``default_alert_code`` if the lab wants to auto-open a
        specific alert on start.
        """
        default_code = (content or {}).get("default_alert_code")
        workspace = services.workspace_context(default_code)

        # A forensics envelope is nested inside SOC state; forensics
        # actions receive/mutate this envelope. We bootstrap it from
        # the alert's case (or an empty case if no alert is open).
        forensics_state = self._forensics.bootstrap(
            lab, {"case": workspace.get("active_case") or {}})

        return self.new_state_envelope(
            forensics=forensics_state,
            workspace=workspace,
            active_alert_code=default_code or "",
            ticked=[],                # checklist slugs the student ticked
            selected_playbook=None,   # alert_type slug the student picked
            root_cause="",            # student's root cause text
            report="",                # student's final report
            closure_checks={},        # last evaluation result
            incident_closed=False,
        )

    def capabilities(self) -> set[str]:
        return {CAP_INSPECTOR}

    def describe_ui(self) -> dict[str, Any]:
        return {"title": "SOC Analyst Console — simulated",
                "soc": True, "forensics": True}

    def welcome(self, state: dict[str, Any]) -> str:
        stats = state.get("workspace", {}).get("stats") or {}
        return (
            "╔══════════════════════════════════════════════════╗\n"
            "║   SECURITY OPERATIONS CENTER — ANALYST CONSOLE    ║\n"
            "╚══════════════════════════════════════════════════╝\n"
            "\n"
            f"Open alerts: {stats.get('open', 0)}\n"
            f"Critical: {stats.get('critical', 0)}   "
            f"High: {stats.get('high', 0)}   "
            f"Medium: {stats.get('medium', 0)}\n"
            "\n"
            "Pick an alert from the queue to begin the investigation."
        )

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        workspace = state.get("workspace", {})
        stats = workspace.get("stats") or {}
        active = workspace.get("active_alert") or {}
        return [
            {"label": "Open alerts", "value": str(stats.get("open", 0))},
            {"label": "Critical",
             "value": str(stats.get("critical", 0)),
             "state": "warn" if stats.get("critical") else None},
            {"label": "Alert",
             "value": (active.get("alert_code") or "—")},
            {"label": "Playbook",
             "value": (state.get("selected_playbook") or "not picked")},
            {"label": "Report",
             "value": ("closed"
                       if state.get("incident_closed") else "pending"),
             "state": ("ok" if state.get("incident_closed")
                       else None)},
        ]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def handle(self, state: dict[str, Any],
               action: Action) -> ActionResult:
        state = dict(state)

        # SOC-specific actions first.
        if action.type == "open_alert":
            return self._open_alert(state, action)
        if action.type == "tick_checklist":
            return self._tick_checklist(state, action)
        if action.type == "select_playbook":
            return self._select_playbook(state, action)
        if action.type == "set_root_cause":
            return self._set_root_cause(state, action)
        if action.type == "close_incident":
            return self._close_incident(state, action)

        # Everything else is a forensics action forwarded through.
        forensics_state = state.get("forensics") or {}
        result = self._forensics.handle(forensics_state, action)
        state["forensics"] = result.new_state
        return ActionResult(output=result.output, new_state=state,
                            events=result.events)

    def _open_alert(self, state: dict[str, Any],
                    action: Action) -> ActionResult:
        alert_code = str(
            (action.payload or {}).get("alert_code") or "").strip()
        workspace = services.workspace_context(alert_code)
        if workspace.get("active_alert") is None:
            return ActionResult(
                output=f"No alert with code {alert_code!r}.",
                new_state=state)
        state["workspace"] = workspace
        state["active_alert_code"] = alert_code

        # Re-bootstrap the forensics envelope with this alert's case.
        state["forensics"] = self._forensics.bootstrap(
            None, {"case": workspace.get("active_case") or {}})

        # Every checklist / playbook / report choice resets to blank on
        # a new alert so the workspace behaves like a fresh triage.
        state["ticked"] = []
        state["selected_playbook"] = None
        state["root_cause"] = ""
        state["report"] = ""
        state["closure_checks"] = {}
        state["incident_closed"] = False

        active = workspace["active_alert"]
        events = [
            {"type": "alert_opened", "alert_code": alert_code,
             "alert_type": active["alert_type"],
             "severity": active["severity"]},
        ]
        return ActionResult(
            output=(f"[QUEUE] Opened {active['alert_code']}: "
                    f"{active['title']} ({active['severity'].upper()})"),
            new_state=state, events=events)

    def _tick_checklist(self, state: dict[str, Any],
                        action: Action) -> ActionResult:
        slug = str((action.payload or {}).get("slug") or "").strip()
        if not slug:
            return ActionResult(output="Missing checklist slug.",
                                new_state=state)
        ticked = list(state.get("ticked") or [])
        if slug in ticked:
            ticked.remove(slug)
            note = "unticked"
        else:
            ticked.append(slug)
            note = "ticked"
        state["ticked"] = ticked
        events = [{"type": "checklist_toggled", "slug": slug,
                   "ticked": slug in ticked}]

        # Fire once every required slug is ticked.
        checklist = ((state.get("workspace") or {}).get("checklist")
                     or [])
        required = {item["slug"] for item in checklist
                    if item.get("is_required")}
        if required and required.issubset(set(ticked)):
            events.append({"type": "checklist_complete"})
        return ActionResult(output=f"[CHECK] {slug} — {note}.",
                            new_state=state, events=events)

    def _select_playbook(self, state: dict[str, Any],
                         action: Action) -> ActionResult:
        alert_type = str(
            (action.payload or {}).get("alert_type") or "").strip()
        if not alert_type:
            return ActionResult(output="Missing playbook alert_type.",
                                new_state=state)
        state["selected_playbook"] = alert_type
        events = [{"type": "playbook_selected",
                   "alert_type": alert_type}]

        # Fire when the analyst picks the matching playbook.
        active = ((state.get("workspace") or {}).get("active_alert")
                  or {})
        if active.get("alert_type") == alert_type:
            events.append({"type": "correct_playbook_selected"})
        return ActionResult(
            output=f"[PLAYBOOK] Loaded {alert_type}.",
            new_state=state, events=events)

    def _set_root_cause(self, state: dict[str, Any],
                        action: Action) -> ActionResult:
        text = str((action.payload or {}).get("text") or "").strip()
        state["root_cause"] = text[:400]
        events = []
        # Cheap early feedback: fire when it matches the alert's type.
        active = ((state.get("workspace") or {}).get("active_alert")
                  or {})
        if active and text and report_engine._root_cause_matches(
                active.get("alert_type") or "", text):
            events.append({"type": "root_cause_named"})
        return ActionResult(output=f"[ROOT CAUSE] {text[:80]}",
                            new_state=state, events=events)

    def _close_incident(self, state: dict[str, Any],
                        action: Action) -> ActionResult:
        payload = action.payload or {}
        # Accept the four report fields either from the payload (JS) or
        # from stored state (terminal/programmatic callers).
        submission = {
            "playbook_alert_type":
                payload.get("playbook_alert_type")
                or state.get("selected_playbook") or "",
            "root_cause":
                payload.get("root_cause") or state.get("root_cause"),
            "report":
                payload.get("report") or state.get("report"),
            "checked":
                payload.get("checked") or state.get("ticked") or [],
        }
        state["report"] = submission["report"]

        active = ((state.get("workspace") or {}).get("active_alert")
                  or {})
        if not active:
            return ActionResult(
                output="No alert is open.", new_state=state)

        # Reconstruct ORM objects lazily — services already know how.
        from app.simulators.soc.models import SocAlert, SocChecklistItem
        alert = SocAlert.query.filter_by(
            alert_code=active["alert_code"]).first()
        if alert is None:
            return ActionResult(
                output="Alert no longer exists.", new_state=state)
        checklist_items = (
            SocChecklistItem.query.filter_by(case_id=alert.case_id).all()
            if alert.case_id else [])

        checks = report_engine.evaluate_report(
            alert, checklist_items, submission)
        state["closure_checks"] = checks
        state["incident_closed"] = bool(checks["all_correct"])

        if checks["all_correct"]:
            output = ("[REPORT] ✅ Incident closed.\n"
                      "Report accepted. Great work, analyst.")
            events = [
                {"type": "incident_closed"},
                {"type": "findings_correct"},
            ]
            for key, ok in checks.items():
                if key != "all_correct" and ok:
                    events.append({"type": f"soc_{key}_ok"})
        else:
            wrong = [k for k, ok in checks.items()
                     if k != "all_correct" and not ok]
            output = ("[REPORT] ✖ Not ready to close: "
                      + ", ".join(wrong) + "\n"
                      "Fix the flagged fields and try again.")
            events = [{"type": "closure_incomplete", "wrong": wrong}]
        return ActionResult(output=output, new_state=state,
                            events=events)
