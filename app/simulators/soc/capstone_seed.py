"""SOC Capstone: Operation Black Phoenix (YC-030.5). Idempotent.

One massive enterprise investigation — a 10-stage coordinated attack
chain. Students reconstruct the entire chain using every engine built
across the SOC and Digital Forensics tracks.

Lab: soc-capstone-black-phoenix (+500 XP, Expert, 9 objectives)
Achievement: SOC Master (+250 bonus XP, soc_lab_completed >= 9)
Certificate: SOC Analyst Completion (requires all 8 SOC labs + capstone)
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.certificates.models import Certificate
from app.extensions import db
from app.labs.forensics.models import (
    ForensicsArtifact,
    ForensicsCase,
    ForensicsEvidence,
    ForensicsSuspect,
    ForensicsTimelineEvent,
)
from app.labs.models import Lab, LabCategory, LabObjective
from app.simulators.soc import scenario_registry
from app.simulators.soc.models import SocAlert, SocChecklistItem

LAB_SLUG = "soc-capstone-black-phoenix"
CASE_LAB_SLUG = "soc-capstone-phoenix-case"
ALERT_CODE = "ALERT-PHOENIX-001"

# =========================================================================
# Case: coordinated attack against fictional Everest Corp
# =========================================================================
CASE_TITLE = "Case #YC-200 — Operation Black Phoenix"
CASE_BRIEFING = (
    "Everest Corp reports suspicious overnight activity: multiple "
    "failed logins, a successful VPN session from an unfamiliar IP, "
    "PowerShell beacons, lateral movement across three workstations, "
    "a 12 GB archive uploaded to an external host, and a ransom note "
    "on the file server. You are the Lead SOC Analyst. Reconstruct "
    "the entire attack chain from phishing to ransomware and contain "
    "the breach."
)

EVIDENCE = [
    ("phishing-email-eml", "document", "urgent-invoice.eml", "eml",
     "mailbox", 15_360, "2026-08-10 18:05", "2026-08-10 18:05",
     "Phishing email with credential-harvesting link.", False, False, 1),
    ("ransom-note-txt", "document", "DECRYPT_FILES.txt", "txt",
     "system", 2_048, "2026-08-11 04:32", "2026-08-11 04:32",
     "Ransom note demanding 2 BTC.", False, False, 2),
    ("exfil-archive", "archive", "everest-data.7z", "7z",
     "system", 12_582_912, "2026-08-11 03:55", "2026-08-11 03:55",
     "Compressed archive staged for exfiltration.", False, True, 3),
]

TIMELINE = [
    ("18:05", "other", "Phishing email arrives — a.karki@everest.corp", None),
    ("18:12", "other", "Employee clicks credential-harvesting link", None),
    ("18:13", "other", "Credentials entered on fake portal", None),
    ("22:47", "login", "VPN login from 45.33.98.12 using stolen creds", None),
    ("22:55", "other", "PowerShell -enc drops Cobalt Strike beacon", None),
    ("23:10", "other", "Privilege escalation via token impersonation", None),
    ("23:25", "other", "Lateral movement — WMI to DC-01, FS-02, WS-14", None),
    ("03:30", "other", "Data collection — 12 GB staged to C:\\Temp", None),
    ("03:55", "other", "Data exfiltration — HTTPS POST to filedump.dark.example", None),
    ("04:30", "other", "Ransomware deployed via PsExec — .locked extension", None),
    ("04:32", "other", "Ransom note dropped", None),
    ("04:40", "logout", "Attacker session terminated", None),
]

SUSPECTS = [
    ("attacker-external", "External Threat Actor", "Unknown",
     "unknown", "Used stolen credentials from a.karki.", True, 1),
    ("a-karki", "Anup Karki", "Finance Manager", "a.karki",
     "Victim of the phishing email. Account compromised.", False, 2),
    ("svc-backup", "svc.backup", "Service Account", "svc.backup",
     "Used for lateral movement after token impersonation.", False, 3),
]

# Artifacts across 10+ source types — the full attack chain.
ARTIFACTS = {
    "browser_history": [
        ("18:12", {"url": "https://secure-everest.phish.example/login",
                   "title": "Everest Corp — Verify Account",
                   "visit_count": 1}, True),
        ("18:10", {"url": "https://mail.everest.corp/inbox",
                   "title": "Webmail — Inbox", "visit_count": 22}, False),
    ],
    "login_history": [
        ("08:30", {"username": "a.karki", "login_at": "08:30",
                   "logout_at": "18:00", "duration": "09h 30m"}, False),
        ("22:47", {"username": "a.karki", "login_at": "22:47",
                   "logout_at": "04:40", "duration": "05h 53m"}, True),
    ],
    "event_log": [
        ("22:47", {"event_id": 4624, "event_type": "user_login",
                   "description": "VPN logon from 45.33.98.12 — a.karki (type 10)",
                   "user": "a.karki"}, True),
        ("22:55", {"event_id": 4688, "event_type": "process_started",
                   "description": "powershell.exe -enc base64payload",
                   "user": "a.karki"}, True),
        ("23:10", {"event_id": 4672, "event_type": "privilege_escalation",
                   "description": "Token impersonation — SeImpersonatePrivilege",
                   "user": "a.karki"}, True),
        ("23:25", {"event_id": 4648, "event_type": "process_started",
                   "description": "WMI lateral movement to DC-01, FS-02, WS-14",
                   "user": "svc.backup"}, True),
        ("03:30", {"event_id": 4663, "event_type": "file_modified",
                   "description": "7z.exe compressing C:\\Shares to C:\\Temp\\everest-data.7z",
                   "user": "svc.backup"}, True),
        ("04:30", {"event_id": 4688, "event_type": "process_started",
                   "description": "PsExec deploying locker.exe across domain",
                   "user": "svc.backup"}, True),
    ],
    "network_dns": [
        ("22:50", {"query": "c2.darkphoenix.example",
                   "response_ip": "185.220.101.42",
                   "domain": "c2.darkphoenix.example"}, True),
        ("03:50", {"query": "filedump.dark.example",
                   "response_ip": "198.51.100.88",
                   "domain": "filedump.dark.example"}, True),
    ],
    "network_https": [
        ("22:58", {"host": "c2.darkphoenix.example",
                   "sni": "c2.darkphoenix.example",
                   "bytes_sent": 4_096, "bytes_received": 524_288}, True),
        ("03:55", {"host": "filedump.dark.example",
                   "sni": "filedump.dark.example",
                   "bytes_sent": 12_582_912, "bytes_received": 512}, True),
    ],
    "network_http": [
        ("04:31", {"method": "POST", "host": "c2.darkphoenix.example",
                   "path": "/api/ransom-deployed",
                   "response_code": 200, "bytes_sent": 256}, True),
    ],
    "downloads": [
        ("03:55", {"filename": "everest-data.7z",
                   "url": "https://filedump.dark.example/upload",
                   "size_bytes": 12_582_912}, True),
    ],
    "usb_history": [
        ("22:40", {"device_name": "SANDISK ULTRA (G:)",
                   "serial_number": "SDK-441X-P9",
                   "connected_at": "22:40", "removed_at": "22:42"}, False),
    ],
    "recent_docs": [
        ("03:28", {"filename": "client-contracts.xlsx",
                   "path": "C:\\Shares\\Finance\\client-contracts.xlsx",
                   "last_accessed_at": "03:28"}, True),
        ("03:29", {"filename": "hr-salaries-2026.xlsx",
                   "path": "C:\\Shares\\HR\\hr-salaries-2026.xlsx",
                   "last_accessed_at": "03:29"}, True),
    ],
}

# Decision config for the IR phases.
IR_SCENARIO = {
    "incident_type": "coordinated_attack",
    "phases": {
        "identification": {
            "correct_actions": ["preserve_evidence", "scan_endpoints",
                                "notify_management"],
            "wrong_actions": ["ignore_alert", "restore_backup"],
        },
        "containment": {
            "correct_actions": ["disconnect_host", "block_ip",
                                "revoke_credentials",
                                "isolate_network_segment"],
            "wrong_actions": ["ignore_alert"],
        },
        "eradication": {
            "correct_actions": ["quarantine_file", "revoke_credentials",
                                "scan_endpoints"],
            "wrong_actions": ["ignore_alert", "restore_backup"],
        },
        "recovery": {
            "correct_actions": ["restore_backup", "reset_password",
                                "patch_vulnerability", "rotate_api_keys"],
            "wrong_actions": ["ignore_alert"],
        },
        "lessons_learned": {
            "correct_actions": ["enable_mfa", "update_firewall_rules",
                                "notify_management"],
            "wrong_actions": [],
        },
    },
}

CHECKLIST = [
    ("identify-phishing", "Identify initial phishing vector", True),
    ("identify-account", "Identify compromised account", True),
    ("identify-malware", "Identify malware execution method", True),
    ("identify-persistence", "Identify persistence mechanism", True),
    ("identify-exfil", "Identify data exfiltration method", True),
    ("identify-c2", "Identify attacker C2 infrastructure", True),
    ("contain-incident", "Contain the incident", True),
    ("recover-env", "Plan environment recovery", True),
    ("write-report", "Write the executive incident report", True),
]

# 9 objectives (+500 XP total).
OBJECTIVES = [
    ("Identify initial access",
     "Determine how the attacker gained their first foothold.",
     "event_emitted", {"event": "ir_phase_completed"},
     ["Check the browser history for the phishing URL.",
      "The credential-harvesting page is the entry point.",
      "Take preserve_evidence + scan_endpoints."], 50),
    ("Identify the compromised account",
     "Name the account the attacker used after phishing.",
     "event_emitted", {"event": "key_suspect_named"},
     ["Three suspects are listed.",
      "The phishing victim's account was used for VPN access.",
      "The external actor used stolen credentials."], 50),
    ("Determine malware execution method",
     "Identify how the Cobalt Strike beacon was deployed.",
     "event_emitted", {"event": "ir_phase_completed"},
     ["Check event log for process execution.",
      "PowerShell -enc dropped the beacon.",
      "Complete the Containment phase."], 50),
    ("Identify persistence mechanism",
     "Determine how the attacker maintained access.",
     "event_emitted", {"event": "ir_phase_completed"},
     ["Token impersonation + svc.backup account.",
      "WMI lateral movement persisted the foothold.",
      "Complete the Eradication phase."], 50),
    ("Determine exfiltration method",
     "Identify how data left the network.",
     "event_emitted", {"event": "ir_phase_completed"},
     ["12 GB compressed with 7z, uploaded via HTTPS.",
      "filedump.dark.example received the archive.",
      "Complete the Recovery phase."], 60),
    ("Identify attacker infrastructure",
     "Name the C2 domain and exfil host.",
     "event_emitted", {"event": "ir_all_phases_complete"},
     ["DNS queries reveal two suspicious domains.",
      "c2.darkphoenix.example and filedump.dark.example.",
      "Complete Lessons Learned to finish all phases."], 60),
    ("Contain the incident",
     "Take the correct containment actions across all phases.",
     "event_emitted", {"event": "ir_correct_action"},
     ["Disconnect affected hosts, block both C2 IPs.",
      "Revoke a.karki and svc.backup credentials.",
      "Isolate the compromised network segment."], 50),
    ("Recover the environment",
     "Restore from backup, rotate credentials, patch.",
     "event_emitted", {"event": "ir_report_submitted"},
     ["Restore from clean backups.",
      "Reset every compromised password + rotate API keys.",
      "Patch the vulnerability that enabled token impersonation."], 60),
    ("Write the executive report",
     "Submit a comprehensive report covering all 9 sections. "
     "Good or Excellent rating closes the incident.",
     "event_emitted", {"event": "incident_closed"},
     ["Cover: Executive Summary, Incident Timeline, Evidence, "
      "Attack Chain, MITRE ATT&CK, Root Cause, Containment, "
      "Recovery, Recommendations.",
      "150+ characters, 4+ sections for maximum report score.",
      "Overall rating must be Good or Excellent."], 70),
]

# All SOC lab slugs for the certificate requirement.
SOC_LAB_SLUGS = [
    "soc-analyst-fundamentals",
    "soc-alert-investigation",
    "soc-incident-response",
    "soc-scenario-ransomware",
    "soc-scenario-phishing",
    "soc-scenario-insider",
    "soc-scenario-dns-tunnel",
    "soc-scenario-malware-beacon",
    "soc-capstone-black-phoenix",
]


# =========================================================================
# Seed functions
# =========================================================================
def _upsert_case() -> ForensicsCase:
    case = ForensicsCase.query.filter_by(lab_slug=CASE_LAB_SLUG).first()
    if case is None:
        case = ForensicsCase(lab_slug=CASE_LAB_SLUG)
        db.session.add(case)
    case.title = CASE_TITLE
    case.briefing = CASE_BRIEFING
    case.workstation_name = "DC-01 / FS-02 / WS-14"
    case.investigator = "Lead Analyst Ayush"
    case.mode = "advanced"
    db.session.flush()

    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    ForensicsSuspect.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for (slug, kind, fn, ext, owner, size, created, modified,
         notes, susp, mod_flag, order) in EVIDENCE:
        db.session.add(ForensicsEvidence(
            case_id=case.id, slug=slug, kind=kind, filename=fn,
            extension=ext, owner=owner, size_bytes=size,
            created_at_display=created, modified_at_display=modified,
            notes=notes, is_suspicious=susp,
            is_modified=mod_flag, display_order=order))
    for at_time, kind, desc, ev_slug in TIMELINE:
        db.session.add(ForensicsTimelineEvent(
            case_id=case.id, at_time=at_time, kind=kind,
            description=desc, evidence_slug=ev_slug))
    for slug, name, role, account, notes, is_key, order in SUSPECTS:
        db.session.add(ForensicsSuspect(
            case_id=case.id, slug=slug, display_name=name,
            role=role, account=account, notes=notes,
            is_key=is_key, display_order=order))
    order = 0
    for source_type, rows in ARTIFACTS.items():
        for at_time, data, is_key in rows:
            order += 1
            a = ForensicsArtifact(
                case_id=case.id, source_type=source_type,
                at_time=at_time, is_key=is_key, sort_order=order)
            a.set_data(data)
            db.session.add(a)

    SocChecklistItem.query.filter_by(case_id=case.id).delete()
    db.session.flush()
    for i, (chk_slug, text, req) in enumerate(CHECKLIST, 1):
        db.session.add(SocChecklistItem(
            case_id=case.id, slug=chk_slug, text=text,
            is_required=req, display_order=i))
    return case


def _upsert_alert(case: ForensicsCase) -> None:
    alert = SocAlert.query.filter_by(alert_code=ALERT_CODE).first()
    if alert is None:
        alert = SocAlert(alert_code=ALERT_CODE)
        db.session.add(alert)
    alert.title = "Operation Black Phoenix — Coordinated Attack"
    alert.alert_type = "data_exfiltration"
    alert.severity = "critical"
    alert.status = "open"
    alert.source = "SIEM + EDR + NDR"
    alert.at_time = "2026-08-10 18:05"
    alert.description = CASE_BRIEFING[:500]
    alert.expected_classification = "confirmed"
    alert.expected_root_cause = (
        "phishing credential theft lateral movement "
        "ransomware exfiltration")
    alert.case_id = case.id
    scenario_registry.register(ALERT_CODE, IR_SCENARIO)


def _upsert_lab(category: LabCategory) -> Lab:
    lab = Lab.query.filter_by(slug=LAB_SLUG).first()
    if lab is None:
        lab = Lab(slug=LAB_SLUG)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = "SOC Capstone: Operation Black Phoenix"
    lab.description = (
        "Lead the investigation of a coordinated enterprise attack — "
        "phishing → credential theft → VPN → PowerShell → privilege "
        "escalation → lateral movement → data exfiltration → "
        "ransomware. Reconstruct the entire attack chain and close "
        "the incident.")
    lab.difficulty = "Expert"
    lab.estimated_minutes = 75
    lab.xp_reward = 500
    lab.display_order = 99
    lab.is_active = True
    lab.simulator_key = "soc"
    lab.is_interactive = True
    prerequisite = Lab.query.filter_by(
        slug="soc-scenario-malware-beacon").first()
    lab.prerequisite_lab_id = prerequisite.id if prerequisite else None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(OBJECTIVES, start=1):
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


def _upsert_achievement() -> None:
    achievement = Achievement.query.filter_by(
        title="SOC Master").first()
    if achievement is None:
        achievement = Achievement(title="SOC Master")
        db.session.add(achievement)
    achievement.description = (
        "Completed Operation Black Phoenix — the SOC Analyst capstone.")
    achievement.icon = "🔥"
    achievement.category = "soc"
    achievement.condition_type = "soc_lab_completed"
    achievement.condition_value = 9
    achievement.bonus_xp = 250
    achievement.is_active = True
    achievement.display_order = 99


def _upsert_certificate() -> None:
    cert = Certificate.query.filter_by(
        slug="soc-analyst-completion").first()
    if cert is None:
        cert = Certificate(slug="soc-analyst-completion")
        db.session.add(cert)
    cert.title = "SOC Analyst Completion"
    cert.description = (
        "Awarded for completing the entire SOC Analyst learning path "
        "including the Operation Black Phoenix capstone.")
    cert.category = "soc"
    cert.certificate_type = "track"
    cert.icon = "shield"
    cert.required_labs = ",".join(SOC_LAB_SLUGS)
    cert.required_xp = 0
    cert.is_active = True
    cert.display_order = 10


def seed_soc_capstone() -> dict[str, int]:
    """Seed the capstone. Idempotent."""
    result = {"case": 0, "alerts": 0, "labs": 0,
              "objectives": 0, "achievements": 0, "certificates": 0}
    category = LabCategory.query.filter_by(
        slug="soc-simulator").first()
    if category is None:
        category = LabCategory(slug="soc-simulator",
                               name="Security Operations Center",
                               display_order=90, is_active=True)
        db.session.add(category)
        db.session.flush()

    case = _upsert_case()
    result["case"] = 1
    _upsert_alert(case)
    result["alerts"] = 1
    _upsert_lab(category)
    result["labs"] = 1
    result["objectives"] = len(OBJECTIVES)
    _upsert_achievement()
    result["achievements"] = 1
    _upsert_certificate()
    result["certificates"] = 1
    db.session.commit()
    return result
