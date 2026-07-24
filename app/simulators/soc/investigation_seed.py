"""SOC Alert Investigation seed (YC-030.2). Idempotent.

Five overnight alerts the student must triage. One is a confirmed
incident backed by a forensics case; two are suspicious; two are
false positives. The student classifies each, assigns severity,
and closes the confirmed incident with a report.

Lab: soc-alert-investigation (+150 XP, Medium, 6 objectives)
Achievement: Alert Hunter (+50 bonus XP, soc_lab_completed >= 2)
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

LAB_SLUG = "soc-alert-investigation"

# ---- Forensics case for the confirmed-incident alert ----
CASE_LAB_SLUG = "soc-investigation-case"
CASE_TITLE = "Case #YC-071 — Suspicious DNS Tunneling"
CASE_BRIEFING = (
    "Automated monitoring flagged high-frequency DNS requests to a "
    "subdomain of an unfamiliar domain. The requests carry encoded "
    "payloads in the query field — possible data exfiltration via "
    "DNS tunneling. Investigate the workstation and determine what "
    "happened."
)

CASE_EVIDENCE = [
    ("dns-capture-pcap", "document", "dns-capture.pcap", "pcap",
     "siem", 524_288, "2026-06-10 23:15", "2026-06-10 23:15",
     "Simulated PCAP — contains encoded DNS queries.", False, False, 1),
]
CASE_TIMELINE = [
    ("23:01", "login", "Session started — r.tamang (VPN)", None),
    ("23:12", "other", "DNS queries begin — t4nnel.example TXT", None),
    ("23:42", "other", "DNS query rate spikes (60 qps)", None),
    ("00:15", "logout", "Session ended — r.tamang", None),
]

# Artifacts for the investigation case.
CASE_ARTIFACTS = {
    "event_log": [
        ("23:01", {"event_id": 4624, "event_type": "user_login",
                   "description": "VPN logon — r.tamang",
                   "user": "r.tamang"}, True),
        ("23:12", {"event_id": 5156, "event_type": "application_started",
                   "description": "dns-beacon.exe started",
                   "user": "r.tamang"}, True),
    ],
    "network_dns": [
        ("23:12", {"query": "aGVsbG8.t4nnel.example",
                   "response_ip": "198.51.100.77",
                   "domain": "t4nnel.example"}, True),
        ("23:42", {"query": "ZXhmaWw.t4nnel.example",
                   "response_ip": "198.51.100.77",
                   "domain": "t4nnel.example"}, True),
    ],
    "login_history": [
        ("23:01", {"username": "r.tamang", "login_at": "23:01",
                   "logout_at": "00:15", "duration": "01h 14m"}, True),
    ],
    "browser_history": [
        ("22:50", {"url": "https://github.com/rtamang",
                   "title": "GitHub — r.tamang",
                   "visit_count": 5}, False),
    ],
}

# ---- Five investigation alerts ----
# (code, title, type, severity, status, source, at_time,
#  description, expected_classification, expected_root_cause, case?)
INVESTIGATION_ALERTS = [
    ("ALERT-INV-0001",
     "Multiple Failed Logins — svc.deploy",
     "multiple_failed_logins", "low", "open", "IAM",
     "2026-06-10 22:30",
     "12 failed login attempts for service account svc.deploy from "
     "CI runner 10.0.4.88 within 5 minutes. Account locked.",
     "false_positive", "service account password rotation", None),

    ("ALERT-INV-0002",
     "PowerShell Encoded Command Execution",
     "suspicious_powershell", "medium", "open", "EDR",
     "2026-06-10 22:55",
     "powershell.exe -enc detected on WORKSTATION-09. Encoded "
     "command decodes to a scheduled-task check — likely legitimate "
     "admin maintenance.",
     "false_positive", "legitimate admin script", None),

    ("ALERT-INV-0003",
     "Suspicious DNS — High-Frequency TXT Queries",
     "dns_tunneling", "critical", "open", "SIEM",
     "2026-06-10 23:12",
     "Over 3 600 TXT queries to *.t4nnel.example in 30 minutes — "
     "pattern consistent with DNS tunneling or C2 beaconing. "
     "Source: WORKSTATION-22, user r.tamang.",
     "confirmed", "dns tunnel exfiltration", "USE_CASE"),

    ("ALERT-INV-0004",
     "USB Mass-Storage Connected After Hours",
     "usb_activity", "medium", "open", "EDR",
     "2026-06-10 23:30",
     "KINGSTON DT (E:) connected to WORKSTATION-14 by user d.moktan. "
     "No files copied per DLP. Correlate with ALERT-2026-0007.",
     "suspicious", "after-hours usb activity", None),

    ("ALERT-INV-0005",
     "Large Outbound File Transfer (9 MB)",
     "suspicious_http_traffic", "high", "open", "NDR",
     "2026-06-11 00:05",
     "9.4 MB HTTPS POST to filedump.example from WORKSTATION-22. "
     "Coincides with DNS tunneling activity. Likely related to "
     "ALERT-INV-0003.",
     "confirmed", "https exfiltration", None),
]

# ---- Investigation checklist (auto-updating, tied to the case) ----
INVESTIGATION_CHECKLIST = [
    ("review-timeline", "Review the unified timeline", True),
    ("review-logs", "Review Windows Event Logs", True),
    ("review-network", "Review network traffic (DNS + HTTPS)", True),
    ("identify-root-cause", "Identify root cause", True),
    ("classify-all", "Classify every alert", True),
    ("complete-report", "Complete the incident report", True),
]

# ---- Objectives ----
INVESTIGATION_OBJECTIVES = [
    ("Open and review every alert",
     "Click each alert in the queue to read its details and classify "
     "at least three of them.",
     "state_flag",
     {"path": "classifications", "min_length": 3},
     ["Five alerts are in the queue.",
      "Open each one — the details panel loads its description.",
      "You need to classify at least the three non-trivial alerts."],
     20),
    ("Correctly classify ALERT-INV-0003",
     "The DNS tunneling alert is the most serious — determine its "
     "classification.",
     "event_emitted",
     {"event": "correct_classification"},
     ["Three options: false_positive, suspicious, or confirmed.",
      "The description says 3 600 TXT queries in 30 min to a "
      "suspicious domain — that's not a false positive.",
      "DNS tunneling with C2 patterns is a confirmed incident."],
     25),
    ("Assign correct severity to the confirmed incident",
     "Match the severity the SOC already flagged for the DNS alert.",
     "event_emitted",
     {"event": "correct_severity_assigned"},
     ["Check the queue — the DNS alert is already marked critical.",
      "Assign the same severity in your triage.",
      "Critical matches the DNS tunneling + exfil pattern."],
     25),
    ("Investigate the linked forensics case",
     "Open every evidence source in the forensics workspace.",
     "event_emitted",
     {"event": "all_sources_opened"},
     ["ALERT-INV-0003 is backed by a forensics case.",
      "Click every source tab (Event Log, DNS, Login, Browser).",
      "The unified timeline shows the full attack chain."],
     25),
    ("Select the correct response playbook",
     "Pick the playbook that matches the confirmed alert's type.",
     "event_emitted",
     {"event": "correct_playbook_selected"},
     ["The alert type is dns_tunneling.",
      "Pick the DNS Tunneling playbook from the dropdown.",
      "It should show Identification → Containment → Eradication → "
      "Recovery → Lessons Learned."],
     25),
    ("Submit the investigation report",
     "Fill root cause, write a 120+ char report touching at least "
     "3 sections, tick all required checklist items, then close.",
     "event_emitted",
     {"event": "findings_correct"},
     ["Root cause: DNS tunnel exfiltration (or similar).",
      "Report must mention Incident Summary, Timeline, Evidence "
      "or Recommendations.",
      "Tick every required checklist item before closing."],
     30),
]


def _upsert_investigation_case() -> ForensicsCase:
    case = ForensicsCase.query.filter_by(lab_slug=CASE_LAB_SLUG).first()
    if case is None:
        case = ForensicsCase(lab_slug=CASE_LAB_SLUG)
        db.session.add(case)
    case.title = CASE_TITLE
    case.briefing = CASE_BRIEFING
    case.workstation_name = "WORKSTATION-22"
    case.investigator = "Investigator Ayush"
    case.mode = "applied"
    db.session.flush()

    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for (slug, kind, filename, ext, owner, size, created, modified,
         notes, suspicious, modified_flag, order) in CASE_EVIDENCE:
        db.session.add(ForensicsEvidence(
            case_id=case.id, slug=slug, kind=kind, filename=filename,
            extension=ext, owner=owner, size_bytes=size,
            created_at_display=created, modified_at_display=modified,
            notes=notes, is_suspicious=suspicious,
            is_modified=modified_flag, display_order=order))
    for at_time, kind, desc, ev_slug in CASE_TIMELINE:
        db.session.add(ForensicsTimelineEvent(
            case_id=case.id, at_time=at_time, kind=kind,
            description=desc, evidence_slug=ev_slug))
    order = 0
    for source_type, rows in CASE_ARTIFACTS.items():
        for at_time, data, is_key in rows:
            order += 1
            artifact = ForensicsArtifact(
                case_id=case.id, source_type=source_type,
                at_time=at_time, is_key=is_key, sort_order=order)
            artifact.set_data(data)
            db.session.add(artifact)
    return case


def _upsert_investigation_alerts(case: ForensicsCase) -> int:
    count = 0
    for (code, title, atype, sev, status, source, at_time,
         desc, expected_cls, expected_rc, case_flag) in INVESTIGATION_ALERTS:
        alert = SocAlert.query.filter_by(alert_code=code).first()
        if alert is None:
            alert = SocAlert(alert_code=code)
            db.session.add(alert)
        alert.title = title
        alert.alert_type = atype
        alert.severity = sev
        alert.status = status
        alert.source = source
        alert.at_time = at_time
        alert.description = desc
        alert.expected_classification = expected_cls
        alert.expected_root_cause = expected_rc
        alert.case_id = case.id if case_flag == "USE_CASE" else None
        count += 1
    # Wire investigation checklist to the case.
    SocChecklistItem.query.filter_by(case_id=case.id).delete()
    db.session.flush()
    for order, (slug, text, required) in enumerate(
            INVESTIGATION_CHECKLIST, start=1):
        db.session.add(SocChecklistItem(
            case_id=case.id, slug=slug, text=text,
            is_required=required, display_order=order))
    return count


def _upsert_investigation_lab(category: LabCategory) -> Lab:
    lab = Lab.query.filter_by(slug=LAB_SLUG).first()
    if lab is None:
        lab = Lab(slug=LAB_SLUG)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = "SOC Analyst: Alert Investigation"
    lab.description = (
        "Triage five overnight alerts as a Tier 1 SOC analyst — "
        "classify each as false positive, suspicious or confirmed, "
        "then investigate the confirmed incident end-to-end.")
    lab.difficulty = "Medium"
    lab.estimated_minutes = 40
    lab.xp_reward = 150
    lab.display_order = 2
    lab.is_active = True
    lab.simulator_key = "soc"
    lab.is_interactive = True
    prerequisite = Lab.query.filter_by(
        slug="soc-analyst-fundamentals").first()
    lab.prerequisite_lab_id = prerequisite.id if prerequisite else None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(INVESTIGATION_OBJECTIVES, start=1):
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


def _upsert_alert_hunter() -> None:
    achievement = Achievement.query.filter_by(
        title="Alert Hunter").first()
    if achievement is None:
        achievement = Achievement(title="Alert Hunter")
        db.session.add(achievement)
    achievement.description = (
        "Successfully triaged a queue of overnight alerts as a "
        "Tier 1 SOC analyst.")
    achievement.icon = "🎯"
    achievement.category = "soc"
    achievement.condition_type = "soc_lab_completed"
    achievement.condition_value = 2
    achievement.bonus_xp = 50
    achievement.is_active = True
    achievement.display_order = 94


def seed_soc_investigation_lab() -> dict[str, int]:
    """Seed the Alert Investigation lab. Idempotent."""
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

    case = _upsert_investigation_case()
    result["case"] = 1
    result["alerts"] = _upsert_investigation_alerts(case)
    _upsert_investigation_lab(category)
    result["labs"] = 1
    result["objectives"] = len(INVESTIGATION_OBJECTIVES)
    _upsert_alert_hunter()
    result["achievements"] = 1
    db.session.commit()
    return result
