"""SOC Incident Response seed (YC-030.3). Idempotent.

Ransomware incident: students progress through all 5 IR phases,
choose actions at each phase, then submit a graded report.

Lab: soc-incident-response (+200 XP, Hard, 6 objectives)
Achievement: Incident Responder (+75 bonus XP, soc_lab_completed >= 3)
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.forensics.models import (
    ForensicsArtifact,
    ForensicsCase,
    ForensicsEvidence,
    ForensicsTimelineEvent,
)
from app.labs.models import Lab, LabCategory, LabObjective
from app.simulators.soc.models import SocAlert, SocChecklistItem

LAB_SLUG = "soc-incident-response"
CASE_LAB_SLUG = "soc-ir-ransomware-case"

# ---- The ransomware forensics case ----
CASE_TITLE = "Case #YC-085 — Ransomware Outbreak"
CASE_BRIEFING = (
    "Three workstations reported file encryption within 15 minutes "
    "of each other. A ransom note demands 0.5 BTC. Investigate the "
    "initial access vector, contain the spread, eradicate the payload, "
    "and plan recovery."
)

CASE_EVIDENCE = [
    ("ransom-note-txt", "document", "README_DECRYPT.txt", "txt",
     "system", 2_048, "2026-07-01 03:15", "2026-07-01 03:15",
     "Ransom note demanding 0.5 BTC.", False, False, 1),
    ("encrypted-db", "document", "clients.db.locked", "locked",
     "system", 52_428_800, "2026-07-01 03:12", "2026-07-01 03:12",
     "Encrypted database — original SHA-256 no longer matches.",
     False, True, 2),
]
CASE_TIMELINE = [
    ("02:47", "login", "RDP session — compromised service account", None),
    ("02:58", "other", "Cobalt Strike beacon dropped", None),
    ("03:05", "other", "Lateral movement — WMI to WORKSTATION-08, -12", None),
    ("03:10", "other", "Encryption begins — *.locked extension", None),
    ("03:15", "other", "Ransom note dropped in every directory", None),
    ("03:22", "logout", "RDP session terminated", None),
]
CASE_ARTIFACTS = {
    "event_log": [
        ("02:47", {"event_id": 4624, "event_type": "user_login",
                   "description": "RDP logon — svc.deploy (type 10)",
                   "user": "svc.deploy"}, True),
        ("02:58", {"event_id": 4688, "event_type": "process_started",
                   "description": "beacon.exe started",
                   "user": "svc.deploy"}, True),
        ("03:05", {"event_id": 4648, "event_type": "privilege_escalation",
                   "description": "WMI lateral movement to WS-08, WS-12",
                   "user": "svc.deploy"}, True),
        ("03:10", {"event_id": 4663, "event_type": "file_modified",
                   "description": "Mass file encryption (*.locked)",
                   "user": "svc.deploy"}, True),
    ],
    "network_dns": [
        ("02:55", {"query": "c2.darkside.example",
                   "response_ip": "203.0.113.50",
                   "domain": "c2.darkside.example"}, True),
    ],
    "network_https": [
        ("02:58", {"host": "c2.darkside.example",
                   "sni": "c2.darkside.example",
                   "bytes_sent": 4_096, "bytes_received": 524_288},
         True),
    ],
    "login_history": [
        ("02:47", {"username": "svc.deploy", "login_at": "02:47",
                   "logout_at": "03:22", "duration": "00h 35m"}, True),
    ],
}

# ---- Incident scenario (phase → correct/wrong actions) ----
IR_SCENARIO = {
    "incident_type": "ransomware",
    "phases": {
        "identification": {
            "correct_actions": ["preserve_evidence", "scan_endpoints"],
            "wrong_actions": ["ignore_alert", "restore_backup"],
        },
        "containment": {
            "correct_actions": ["disconnect_host",
                                "isolate_network_segment",
                                "block_ip"],
            "wrong_actions": ["ignore_alert"],
        },
        "eradication": {
            "correct_actions": ["quarantine_file",
                                "revoke_credentials",
                                "scan_endpoints"],
            "wrong_actions": ["ignore_alert", "restore_backup"],
        },
        "recovery": {
            "correct_actions": ["restore_backup", "reset_password",
                                "patch_vulnerability"],
            "wrong_actions": ["ignore_alert"],
        },
        "lessons_learned": {
            "correct_actions": ["enable_mfa",
                                "update_firewall_rules",
                                "notify_management"],
            "wrong_actions": [],
        },
    },
}

# ---- Alert ----
ALERT_CODE = "ALERT-IR-0001"
ALERT_TITLE = "Ransomware Outbreak — 3 Workstations Encrypted"

# ---- Checklist ----
IR_CHECKLIST = [
    ("identify-vector", "Identify initial access vector", True),
    ("contain-spread", "Contain lateral movement", True),
    ("eradicate-payload", "Eradicate the ransomware payload", True),
    ("plan-recovery", "Plan recovery from backups", True),
    ("write-report", "Submit the incident report", True),
]

# ---- Objectives ----
IR_OBJECTIVES = [
    ("Complete the Identification phase",
     "Review evidence, preserve it, and scan endpoints.",
     "event_emitted",
     {"event": "ir_phase_completed"},
     ["Open the Evidence sources + Timeline panels.",
      "Take the 'preserve_evidence' and 'scan_endpoints' actions.",
      "Click 'Complete Phase' when you've identified the vector."],
     30),
    ("Complete the Containment phase",
     "Disconnect affected hosts, isolate the network segment, "
     "and block the C2 IP.",
     "event_emitted",
     {"event": "ir_phase_completed"},
     ["You need to contain the spread before eradicating.",
      "Disconnect the host, isolate the segment, block the C2 IP.",
      "Click 'Complete Phase' to advance."],
     30),
    ("Complete the Eradication phase",
     "Quarantine the payload and revoke compromised credentials.",
     "event_emitted",
     {"event": "ir_phase_completed"},
     ["Quarantine beacon.exe, revoke svc.deploy credentials.",
      "Scan endpoints to confirm no residual malware.",
      "Click 'Complete Phase'."],
     30),
    ("Complete all five IR phases",
     "Recovery and Lessons Learned must also be done.",
     "event_emitted",
     {"event": "ir_all_phases_complete"},
     ["Recovery: restore_backup, reset_password, patch_vulnerability.",
      "Lessons Learned: enable_mfa, update_firewall_rules, "
      "notify_management.",
      "All five phases must be marked complete."],
     30),
    ("Achieve a 'Good' or 'Excellent' rating",
     "Your score depends on correct decisions + report quality.",
     "event_emitted",
     {"event": "ir_report_submitted"},
     ["Take the correct actions in each phase — wrong ones cost points.",
      "Write a report covering Executive Summary, Incident Timeline, "
      "Evidence, Root Cause, Containment, Recovery, Recommendations.",
      "150+ characters, 4+ sections = maximum report score."],
     40),
    ("Close the incident",
     "The incident closes automatically when your score is Good "
     "or Excellent.",
     "event_emitted",
     {"event": "incident_closed"},
     ["A 'Needs Improvement' rating won't close the incident.",
      "Go back and take more correct actions to boost your score.",
      "Resubmit the report after improving."],
     40),
]


def _upsert_ir_case() -> ForensicsCase:
    case = ForensicsCase.query.filter_by(lab_slug=CASE_LAB_SLUG).first()
    if case is None:
        case = ForensicsCase(lab_slug=CASE_LAB_SLUG)
        db.session.add(case)
    case.title = CASE_TITLE
    case.briefing = CASE_BRIEFING
    case.workstation_name = "WORKSTATION-05"
    case.investigator = "Investigator Ayush"
    case.mode = "applied"
    db.session.flush()

    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for (slug, kind, fn, ext, owner, size, created, modified,
         notes, susp, mod_flag, order) in CASE_EVIDENCE:
        db.session.add(ForensicsEvidence(
            case_id=case.id, slug=slug, kind=kind, filename=fn,
            extension=ext, owner=owner, size_bytes=size,
            created_at_display=created, modified_at_display=modified,
            notes=notes, is_suspicious=susp,
            is_modified=mod_flag, display_order=order))
    for at_time, kind, desc, ev_slug in CASE_TIMELINE:
        db.session.add(ForensicsTimelineEvent(
            case_id=case.id, at_time=at_time, kind=kind,
            description=desc, evidence_slug=ev_slug))
    order = 0
    for source_type, rows in CASE_ARTIFACTS.items():
        for at_time, data, is_key in rows:
            order += 1
            a = ForensicsArtifact(
                case_id=case.id, source_type=source_type,
                at_time=at_time, is_key=is_key, sort_order=order)
            a.set_data(data)
            db.session.add(a)
    return case


def _upsert_ir_alert(case: ForensicsCase) -> None:
    alert = SocAlert.query.filter_by(alert_code=ALERT_CODE).first()
    if alert is None:
        alert = SocAlert(alert_code=ALERT_CODE)
        db.session.add(alert)
    alert.title = ALERT_TITLE
    alert.alert_type = "possible_malware"
    alert.severity = "critical"
    alert.status = "open"
    alert.source = "EDR"
    alert.at_time = "2026-07-01 03:10"
    alert.description = (
        "Three workstations encrypted within 15 minutes — ransomware "
        "outbreak. Ransom note demands 0.5 BTC. Immediate IR required.")
    alert.expected_classification = "confirmed"
    alert.expected_root_cause = "ransomware cobalt strike"
    alert.case_id = case.id

    # Checklist
    SocChecklistItem.query.filter_by(case_id=case.id).delete()
    db.session.flush()
    for order, (slug, text, required) in enumerate(IR_CHECKLIST, 1):
        db.session.add(SocChecklistItem(
            case_id=case.id, slug=slug, text=text,
            is_required=required, display_order=order))


def _upsert_ir_lab(category: LabCategory) -> Lab:
    lab = Lab.query.filter_by(slug=LAB_SLUG).first()
    if lab is None:
        lab = Lab(slug=LAB_SLUG)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = "SOC Analyst: Incident Response"
    lab.description = (
        "Lead the response to a ransomware outbreak — progress "
        "through all five IR phases (Identification → Containment → "
        "Eradication → Recovery → Lessons Learned), make action "
        "decisions, and submit a graded incident report.")
    lab.difficulty = "Hard"
    lab.estimated_minutes = 50
    lab.xp_reward = 200
    lab.display_order = 3
    lab.is_active = True
    lab.simulator_key = "soc"
    lab.is_interactive = True
    prerequisite = Lab.query.filter_by(
        slug="soc-alert-investigation").first()
    lab.prerequisite_lab_id = prerequisite.id if prerequisite else None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(IR_OBJECTIVES, start=1):
        objective = LabObjective.query.filter_by(
            lab_id=lab.id, title=title).first()
        if objective is None:
            objective = LabObjective(lab_id=lab.id, title=title)
            db.session.add(objective)
        objective.description = instruction
        objective.instruction = instruction
        objective.display_order = order
        objective.validator_type = vtype
        objective.set_validator_data(vdata)
        objective.hint1 = hints[0] if len(hints) > 0 else None
        objective.hint2 = hints[1] if len(hints) > 1 else None
        objective.hint3 = hints[2] if len(hints) > 2 else None
        objective.xp_reward = xp
        objective.is_optional = False
    return lab


def _upsert_responder_achievement() -> None:
    achievement = Achievement.query.filter_by(
        title="Incident Responder").first()
    if achievement is None:
        achievement = Achievement(title="Incident Responder")
        db.session.add(achievement)
    achievement.description = (
        "Led a full incident response through all five IR phases "
        "and closed the incident with a passing score.")
    achievement.icon = "🛡"
    achievement.category = "soc"
    achievement.condition_type = "soc_lab_completed"
    achievement.condition_value = 3
    achievement.bonus_xp = 75
    achievement.is_active = True
    achievement.display_order = 95


def seed_soc_incident_response() -> dict[str, int]:
    """Seed the IR lab. Idempotent."""
    result = {"case": 0, "alerts": 0, "labs": 0,
              "objectives": 0, "achievements": 0}
    category = LabCategory.query.filter_by(
        slug="soc-simulator").first()
    if category is None:
        category = LabCategory(slug="soc-simulator",
                               name="Security Operations Center",
                               display_order=90, is_active=True)
        db.session.add(category)
        db.session.flush()

    case = _upsert_ir_case()
    result["case"] = 1
    _upsert_ir_alert(case)
    result["alerts"] = 1
    _upsert_ir_lab(category)
    result["labs"] = 1
    result["objectives"] = len(IR_OBJECTIVES)
    _upsert_responder_achievement()
    result["achievements"] = 1
    # Register the scenario decisions in the runtime registry.
    from app.simulators.soc import scenario_registry
    scenario_registry.register(ALERT_CODE, IR_SCENARIO)

    db.session.commit()
    return result
