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
            # YC-030.2 investigation state — tracks per-alert decisions.
            classifications={},       # alert_code → "false_positive"|"suspicious"|"confirmed"
            severity_assignments={},  # alert_code → severity string
            escalated=[],             # alert_codes escalated
            investigation_checks={},  # last triage-validation result
            # YC-030.3 Incident Response state.
            ir_decisions=[],          # list of graded decision dicts
            ir_completed_phases=[],   # phase slugs completed
            ir_score=None,            # final score dict (on submit)
            # YC-030.4 hint tracking.
            hints_used=0,
            # YC-030.6 Threat Hunting state.
            hunt_bookmarks=[],
            hunt_notes=[],
            hunt_searches=[],
            hunt_mitre_mapped=[],
            hunt_report=None,
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
        # YC-030.2: alert-triage actions.
        if action.type == "classify_alert":
            return self._classify_alert(state, action)
        if action.type == "assign_severity":
            return self._assign_severity(state, action)
        if action.type == "escalate_alert":
            return self._escalate_alert(state, action)
        if action.type == "mark_false_positive":
            return self._mark_false_positive(state, action)
        # YC-030.3: Incident Response workflow actions.
        if action.type == "take_action":
            return self._take_action(state, action)
        if action.type == "complete_phase":
            return self._complete_phase(state, action)
        if action.type == "submit_ir_report":
            return self._submit_ir_report(state, action)
        # YC-030.4: Hint system.
        if action.type == "use_hint":
            return self._use_hint(state, action)
        # YC-030.3.5: Case Management actions.
        if action.type == "open_case":
            return self._open_case(state, action)
        if action.type == "assign_case":
            return self._assign_case(state, action)
        if action.type == "add_case_note":
            return self._add_case_note(state, action)
        if action.type == "link_case_evidence":
            return self._link_case_evidence(state, action)
        if action.type == "escalate_case":
            return self._escalate_case(state, action)
        if action.type == "close_case":
            return self._close_case(state, action)
        # YC-030.6: Threat Hunting actions.
        if action.type == "search_telemetry":
            return self._search_telemetry(state, action)
        if action.type == "bookmark":
            return self._bookmark(state, action)
        if action.type == "unbookmark":
            return self._unbookmark(state, action)
        if action.type == "add_hunt_note":
            return self._add_hunt_note(state, action)
        if action.type == "map_mitre":
            return self._map_mitre(state, action)
        if action.type == "submit_hunt_report":
            return self._submit_hunt_report(state, action)
        # YC-030.7: Blue Team Assessment.
        if action.type == "submit_assessment":
            return self._submit_assessment(state, action)

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


    # ------------------------------------------------------------------
    # YC-030.2 — Alert Investigation actions
    # ------------------------------------------------------------------


VALID_CLASSIFICATIONS = ("false_positive", "suspicious", "confirmed")

def _classify_alert(self, state: dict[str, Any],
                    action: Action) -> ActionResult:
    alert_code = str(
        (action.payload or {}).get("alert_code") or "").strip()
    classification = str(
        (action.payload or {}).get("classification") or "").strip()
    if not alert_code or classification not in VALID_CLASSIFICATIONS:
        return ActionResult(
            output=f"Invalid classification '{classification}'.",
            new_state=state)
    classifications = dict(state.get("classifications") or {})
    classifications[alert_code] = classification
    state["classifications"] = classifications

    events = [{
        "type": "alert_classified",
        "alert_code": alert_code,
        "classification": classification,
    }]
    # Check if the classification matches the expected one from the
    # alert's metadata (seeded in the alert's description JSON or
    # inferred from severity).
    workspace = state.get("workspace") or {}
    active = workspace.get("active_alert") or {}
    if (alert_code == active.get("alert_code")
            and _expected_classification(active) == classification):
        events.append({"type": "correct_classification",
                       "alert_code": alert_code})
    return ActionResult(
        output=f"[TRIAGE] {alert_code} → {classification}",
        new_state=state, events=events)

def _assign_severity(self, state: dict[str, Any],
                     action: Action) -> ActionResult:
    from app.simulators.soc.models import SEVERITIES
    alert_code = str(
        (action.payload or {}).get("alert_code") or "").strip()
    severity = str(
        (action.payload or {}).get("severity") or "").strip()
    if not alert_code or severity not in SEVERITIES:
        return ActionResult(
            output=f"Invalid severity '{severity}'.",
            new_state=state)
    assignments = dict(state.get("severity_assignments") or {})
    assignments[alert_code] = severity
    state["severity_assignments"] = assignments
    events = [{"type": "severity_assigned",
               "alert_code": alert_code, "severity": severity}]
    # Check match.
    workspace = state.get("workspace") or {}
    active = workspace.get("active_alert") or {}
    if (alert_code == active.get("alert_code")
            and active.get("severity") == severity):
        events.append({"type": "correct_severity_assigned",
                       "alert_code": alert_code})
    return ActionResult(
        output=f"[SEVERITY] {alert_code} → {severity}",
        new_state=state, events=events)

def _escalate_alert(self, state: dict[str, Any],
                    action: Action) -> ActionResult:
    alert_code = str(
        (action.payload or {}).get("alert_code") or "").strip()
    if not alert_code:
        return ActionResult(output="Missing alert_code.",
                            new_state=state)
    escalated = list(state.get("escalated") or [])
    if alert_code not in escalated:
        escalated.append(alert_code)
    state["escalated"] = escalated
    return ActionResult(
        output=f"[ESCALATE] {alert_code} escalated to Tier 2.",
        new_state=state,
        events=[{"type": "alert_escalated",
                 "alert_code": alert_code}])

def _mark_false_positive(self, state: dict[str, Any],
                         action: Action) -> ActionResult:
    """Convenience shortcut — classify as false_positive + close."""
    alert_code = str(
        (action.payload or {}).get("alert_code") or "").strip()
    if not alert_code:
        return ActionResult(output="Missing alert_code.",
                            new_state=state)
    classifications = dict(state.get("classifications") or {})
    classifications[alert_code] = "false_positive"
    state["classifications"] = classifications
    events = [
        {"type": "alert_classified", "alert_code": alert_code,
         "classification": "false_positive"},
        {"type": "alert_marked_false_positive",
         "alert_code": alert_code},
    ]
    workspace = state.get("workspace") or {}
    active = workspace.get("active_alert") or {}
    if (alert_code == active.get("alert_code")
            and _expected_classification(active) == "false_positive"):
        events.append({"type": "correct_classification",
                       "alert_code": alert_code})
    return ActionResult(
        output=f"[FALSE POSITIVE] {alert_code} closed.",
        new_state=state, events=events)


def _expected_classification(alert: dict[str, Any]) -> str:
    """Derive the expected classification from the alert metadata.

    Convention: ``expected_classification`` in the alert dict (set
    by the seed); falls back to severity-based heuristic.
    """
    explicit = (alert.get("expected_classification") or "").strip()
    if explicit in ("false_positive", "suspicious", "confirmed"):
        return explicit
    sev = (alert.get("severity") or "").lower()
    if sev in ("critical", "high"):
        return "confirmed"
    if sev == "medium":
        return "suspicious"
    return "false_positive"


# Patch new methods onto the class (appended to avoid large str_replace).
SOCSimulator._classify_alert = _classify_alert
SOCSimulator._assign_severity = _assign_severity
SOCSimulator._escalate_alert = _escalate_alert
SOCSimulator._mark_false_positive = _mark_false_positive


# ------------------------------------------------------------------
# YC-030.3 — Incident Response action handlers
# ------------------------------------------------------------------
def _take_action(self, state, action):
    """Student picks an IR action (disconnect_host, block_ip, etc.)."""
    from app.simulators.soc import decision_engine, incident_engine
    act = str((action.payload or {}).get("action") or "").strip()
    if not act:
        return ActionResult(output="Missing action.", new_state=state)
    phase = incident_engine.current_phase(
        state.get("ir_completed_phases") or [])
    if phase is None:
        return ActionResult(
            output="All phases complete — submit your report.",
            new_state=state)

    # Get correct/wrong actions for the current phase from the
    # scenario registry (keyed by alert code).
    from app.simulators.soc import scenario_registry
    alert_code = state.get("active_alert_code") or ""
    scenario = scenario_registry.get(alert_code)
    if not scenario:
        # Fallback: check workspace (backward compat with IR seed).
        scenario = ((state.get("workspace") or {})
                    .get("incident_scenario") or {})
    phase_actions = (scenario.get("phases") or {}).get(phase) or {}
    correct = phase_actions.get("correct_actions") or []
    wrong = phase_actions.get("wrong_actions") or []

    grade = decision_engine.grade_decision(act, correct, wrong)
    decisions = list(state.get("ir_decisions") or [])
    decisions.append(grade)
    state["ir_decisions"] = decisions

    events = [{"type": "ir_action_taken", "action": act,
               "phase": phase, "correct": grade["correct"],
               "points": grade["points"]}]
    if grade["correct"]:
        events.append({"type": "ir_correct_action"})
    return ActionResult(
        output=grade["feedback"], new_state=state, events=events)


def _complete_phase(self, state, action):
    """Student signals they've finished the current IR phase."""
    from app.simulators.soc import incident_engine
    completed = list(state.get("ir_completed_phases") or [])
    cur = incident_engine.current_phase(completed)
    if cur is None:
        return ActionResult(
            output="All phases already complete.", new_state=state)
    completed.append(cur)
    state["ir_completed_phases"] = completed
    events = [{"type": "ir_phase_completed", "phase": cur}]
    if incident_engine.all_phases_complete(completed):
        events.append({"type": "ir_all_phases_complete"})
    nxt = incident_engine.current_phase(completed)
    label = incident_engine.PHASE_LABELS.get(
        nxt, "Report") if nxt else "Submit Report"
    return ActionResult(
        output=f"[PHASE] {incident_engine.PHASE_LABELS.get(cur, cur)} "
               f"✓ complete → next: {label}",
        new_state=state, events=events)


def _submit_ir_report(self, state, action):
    """Student submits the final IR report."""
    from app.simulators.soc import score_engine
    report = str((action.payload or {}).get("report") or "").strip()
    if len(report) < 50:
        return ActionResult(
            output="Report too short (minimum 150 characters).",
            new_state=state)
    completed = state.get("ir_completed_phases") or []
    decisions = state.get("ir_decisions") or []
    hints_used = int(state.get("hints_used") or 0)
    score = score_engine.compute_final_score(
        decisions, report, len(completed), hints_used=hints_used)
    state["ir_score"] = score
    state["report"] = report

    events = [{"type": "ir_report_submitted",
               "rating": score["rating"]}]
    if score["rating"] in ("Excellent", "Good"):
        events.append({"type": "findings_correct"})
        events.append({"type": "incident_closed"})
        state["incident_closed"] = True
    return ActionResult(
        output=(f"[SCORE] {score['rating']} — "
                f"{score['total']}/{score['max']} points "
                f"({score['ratio']:.0%})"),
        new_state=state, events=events)


SOCSimulator._take_action = _take_action
SOCSimulator._complete_phase = _complete_phase
SOCSimulator._submit_ir_report = _submit_ir_report


# ------------------------------------------------------------------
# YC-030.3.5 — Case Management action handlers
# ------------------------------------------------------------------
def _open_case(self, state, action):
    from app.simulators.soc import case_manager
    code = str((action.payload or {}).get("case_code") or "").strip()
    title = str((action.payload or {}).get("title") or "").strip()
    severity = str((action.payload or {}).get("severity") or "medium")
    if not code or not title:
        return ActionResult(output="Missing case_code or title.",
                            new_state=state)
    alert_code = state.get("active_alert_code") or ""
    linked = [alert_code] if alert_code else []
    case_manager.create_case(code, title, severity, linked)
    state["active_case_code"] = code
    return ActionResult(
        output=f"[CASE] {code} opened: {title}",
        new_state=state,
        events=[{"type": "case_opened", "case_code": code}])


def _assign_case(self, state, action):
    from app.simulators.soc import case_manager
    code = str((action.payload or {}).get("case_code") or
               state.get("active_case_code") or "").strip()
    analyst = str((action.payload or {}).get("analyst") or "").strip()
    if not code or not analyst:
        return ActionResult(output="Missing case_code or analyst.",
                            new_state=state)
    case = case_manager.find_by_code(code)
    if case is None:
        return ActionResult(output=f"No case {code}.",
                            new_state=state)
    case_manager.assign_case(case, analyst)
    return ActionResult(
        output=f"[CASE] {code} assigned to {analyst}.",
        new_state=state,
        events=[{"type": "case_assigned", "case_code": code,
                 "analyst": analyst}])


def _add_case_note(self, state, action):
    from app.simulators.soc import case_manager
    code = str((action.payload or {}).get("case_code") or
               state.get("active_case_code") or "").strip()
    text = str((action.payload or {}).get("text") or "").strip()
    author = str((action.payload or {}).get("author") or "analyst")
    if not code or not text:
        return ActionResult(output="Missing case_code or text.",
                            new_state=state)
    case = case_manager.find_by_code(code)
    if case is None:
        return ActionResult(output=f"No case {code}.",
                            new_state=state)
    case_manager.add_note(case, author, text[:400])
    return ActionResult(
        output=f"[CASE NOTE] {text[:80]}",
        new_state=state,
        events=[{"type": "case_note_added", "case_code": code}])


def _link_case_evidence(self, state, action):
    from app.simulators.soc import case_manager
    code = str((action.payload or {}).get("case_code") or
               state.get("active_case_code") or "").strip()
    ref = str((action.payload or {}).get("evidence_ref") or "").strip()
    if not code or not ref:
        return ActionResult(output="Missing case_code or evidence_ref.",
                            new_state=state)
    case = case_manager.find_by_code(code)
    if case is None:
        return ActionResult(output=f"No case {code}.",
                            new_state=state)
    case_manager.link_evidence(case, ref)
    return ActionResult(
        output=f"[CASE] Evidence '{ref}' linked to {code}.",
        new_state=state,
        events=[{"type": "case_evidence_linked", "case_code": code,
                 "evidence_ref": ref}])


def _escalate_case(self, state, action):
    from app.simulators.soc import case_manager
    code = str((action.payload or {}).get("case_code") or
               state.get("active_case_code") or "").strip()
    if not code:
        return ActionResult(output="Missing case_code.",
                            new_state=state)
    case = case_manager.find_by_code(code)
    if case is None:
        return ActionResult(output=f"No case {code}.",
                            new_state=state)
    case_manager.escalate_case(case)
    return ActionResult(
        output=f"[CASE] {code} escalated.",
        new_state=state,
        events=[{"type": "case_escalated", "case_code": code}])


def _close_case(self, state, action):
    from app.simulators.soc import case_manager
    code = str((action.payload or {}).get("case_code") or
               state.get("active_case_code") or "").strip()
    if not code:
        return ActionResult(output="Missing case_code.",
                            new_state=state)
    case = case_manager.find_by_code(code)
    if case is None:
        return ActionResult(output=f"No case {code}.",
                            new_state=state)
    case_manager.close_case(case)
    return ActionResult(
        output=f"[CASE] {code} closed.",
        new_state=state,
        events=[{"type": "case_closed", "case_code": code}])


SOCSimulator._open_case = _open_case
SOCSimulator._assign_case = _assign_case
SOCSimulator._add_case_note = _add_case_note
SOCSimulator._link_case_evidence = _link_case_evidence
SOCSimulator._escalate_case = _escalate_case
SOCSimulator._close_case = _close_case


# ------------------------------------------------------------------
# YC-030.4 — Hint system
# ------------------------------------------------------------------
HINT_PENALTY = 5  # points deducted per hint used

def _use_hint(self, state, action):
    """Student requests a hint — tracked for scoring."""
    hints_used = int(state.get("hints_used") or 0) + 1
    state["hints_used"] = hints_used
    return ActionResult(
        output=f"[HINT] Hint #{hints_used} used — "
               f"{HINT_PENALTY} points will be deducted from final score.",
        new_state=state,
        events=[{"type": "hint_used", "count": hints_used}])

SOCSimulator._use_hint = _use_hint


# ------------------------------------------------------------------
# YC-030.6 — Threat Hunting action handlers
# ------------------------------------------------------------------
def _search_telemetry(self, state, action):
    from app.simulators.soc import hunt_engine
    query = str((action.payload or {}).get("query") or "").strip()
    field = (action.payload or {}).get("field") or None
    if not query:
        return ActionResult(output="Empty search query.",
                            new_state=state)
    case = (state.get("forensics") or {}).get("case") or {}
    artifacts = case.get("artifacts") or []
    results = hunt_engine.search_telemetry(artifacts, query, field)
    searches = list(state.get("hunt_searches") or [])
    searches.append({"query": query, "field": field,
                     "results": len(results)})
    state["hunt_searches"] = searches
    events = [{"type": "telemetry_searched", "query": query,
               "results": len(results)}]
    if results:
        events.append({"type": "hunt_evidence_found"})
    return ActionResult(
        output=f"[SEARCH] '{query}' → {len(results)} result(s).",
        new_state=state, events=events)


def _bookmark(self, state, action):
    from app.simulators.soc import hunt_engine
    ref = str((action.payload or {}).get("ref") or "").strip()
    label = str((action.payload or {}).get("label") or ref)[:200]
    if not ref:
        return ActionResult(output="Missing bookmark ref.",
                            new_state=state)
    state = hunt_engine.add_bookmark(state, ref, label)
    return ActionResult(
        output=f"[BOOKMARK] {label[:60]}",
        new_state=state,
        events=[{"type": "evidence_bookmarked", "ref": ref}])


def _unbookmark(self, state, action):
    from app.simulators.soc import hunt_engine
    ref = str((action.payload or {}).get("ref") or "").strip()
    if not ref:
        return ActionResult(output="Missing ref.", new_state=state)
    state = hunt_engine.remove_bookmark(state, ref)
    return ActionResult(output=f"[UNBOOKMARK] {ref}",
                        new_state=state)


def _add_hunt_note(self, state, action):
    from app.simulators.soc import hunt_engine
    note = (action.payload or {})
    if not note.get("title") and not note.get("observation"):
        return ActionResult(output="Empty note.", new_state=state)
    state = hunt_engine.add_hunt_note(state, note)
    return ActionResult(
        output=f"[NOTE] {(note.get('title') or '')[:60]}",
        new_state=state,
        events=[{"type": "hunt_note_added"}])


def _map_mitre(self, state, action):
    technique_id = str(
        (action.payload or {}).get("technique_id") or "").strip()
    if not technique_id:
        return ActionResult(output="Missing technique_id.",
                            new_state=state)
    mapped = list(state.get("hunt_mitre_mapped") or [])
    if technique_id not in mapped:
        mapped.append(technique_id)
    state["hunt_mitre_mapped"] = mapped
    events = [{"type": "mitre_technique_mapped",
               "technique_id": technique_id}]
    # Check if all expected techniques are mapped.
    alert_code = state.get("active_alert_code") or ""
    from app.simulators.soc import hunt_engine as he
    expected = he.get_mitre(alert_code)
    expected_ids = {m.get("technique_id") for m in expected}
    if expected_ids and expected_ids.issubset(set(mapped)):
        events.append({"type": "all_mitre_mapped"})
    return ActionResult(
        output=f"[MITRE] {technique_id} mapped.",
        new_state=state, events=events)


def _submit_hunt_report(self, state, action):
    from app.simulators.soc import hunt_engine
    report = str((action.payload or {}).get("report") or "").strip()
    if len(report) < 50:
        return ActionResult(
            output="Report too short (minimum 150 characters).",
            new_state=state)
    iocs_found = len([s for s in (state.get("hunt_searches") or [])
                      if s.get("results", 0) > 0])
    mitre_mapped = len(state.get("hunt_mitre_mapped") or [])
    bookmarks = len(state.get("hunt_bookmarks") or [])
    hints_used = int(state.get("hints_used") or 0)
    score = hunt_engine.score_hunt_report(
        report, iocs_found, mitre_mapped, bookmarks, hints_used)
    state["hunt_report"] = score
    state["report"] = report
    events = [{"type": "hunt_report_submitted",
               "rating": score["rating"]}]
    if score["rating"] in ("Excellent", "Good", "Pass"):
        events.append({"type": "findings_correct"})
        events.append({"type": "incident_closed"})
        state["incident_closed"] = True
    return ActionResult(
        output=(f"[HUNT SCORE] {score['rating']} — "
                f"{score['total']}/{score['max']} points "
                f"({score['ratio']:.0%})"),
        new_state=state, events=events)


SOCSimulator._search_telemetry = _search_telemetry
SOCSimulator._bookmark = _bookmark
SOCSimulator._unbookmark = _unbookmark
SOCSimulator._add_hunt_note = _add_hunt_note
SOCSimulator._map_mitre = _map_mitre
SOCSimulator._submit_hunt_report = _submit_hunt_report


# ------------------------------------------------------------------
# YC-030.7 — Blue Team Assessment
# ------------------------------------------------------------------
def _submit_assessment(self, state, action):
    """Final assessment submission — scores everything + records result."""
    from app.simulators.soc import assessment_engine, scenario_registry
    report = str((action.payload or {}).get("report") or "").strip()
    if len(report) < 100:
        return ActionResult(
            output="Assessment report too short (minimum 200 characters).",
            new_state=state)
    state["report"] = report
    alert_code = state.get("active_alert_code") or ""
    expected = scenario_registry.get(alert_code)
    score = assessment_engine.score_assessment(state, expected)
    state["assessment_score"] = score
    events = [{"type": "assessment_submitted",
               "grade": score["grade"],
               "score": score["total"]}]
    if score["grade"] in ("Excellent", "Pass"):
        events.append({"type": "findings_correct"})
        events.append({"type": "incident_closed"})
        state["incident_closed"] = True
    return ActionResult(
        output=(f"[ASSESSMENT] {score['grade']} — "
                f"{score['total']}/{score['max']} "
                f"({score['ratio']:.0%})"),
        new_state=state, events=events)


SOCSimulator._submit_assessment = _submit_assessment
