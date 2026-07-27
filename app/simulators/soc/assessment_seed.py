"""Blue Team Assessment seed (YC-030.7). Idempotent.

One massive enterprise environment with 8 alerts (5 real incidents,
3 false positives). Students investigate independently — no guided
checklist, no highlighted objectives.

Lab: soc-blue-team-assessment (+750 XP, Expert, 8 objectives)
Achievement: Blue Team Expert (+300 bonus XP)
Certificate: Blue Team Analyst
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
from app.simulators.soc.models import SocAlert

LAB_SLUG = "soc-blue-team-assessment"
CASE_LAB_SLUG = "soc-assessment-enterprise-case"
PRIMARY_ALERT = "ASSESS-001"

CASE_TITLE = "Blue Team Assessment — Enterprise Investigation"
CASE_BRIEFING = (
    "You are the lead Blue Team analyst for Koshi Corp. Overnight "
    "monitoring flagged 8 alerts across the enterprise. Some are "
    "real attacks; some are false positives. You have no guided "
    "checklist — investigate independently, classify every alert, "
    "contain threats, and submit a comprehensive executive report. "
    "Your performance determines your certification grade."
)

EVIDENCE = [
    ("mail-server-log", "document", "mail-server.log", "log",
     "siem", 1_048_576, "2026-09-15 00:00", "2026-09-15 06:00",
     "12-hour mail server log excerpt.", False, False, 1),
    ("network-capture", "document", "enterprise-traffic.pcap", "pcap",
     "ndr", 8_388_608, "2026-09-15 00:00", "2026-09-15 06:00",
     "6-hour network capture.", False, False, 2),
    ("dc01-eventlog", "document", "DC01-Security.evtx", "evtx",
     "siem", 2_097_152, "2026-09-15 00:00", "2026-09-15 06:00",
     "Domain controller security event log.", False, False, 3),
]

SUSPECTS = [
    ("external-apt", "APT Group — Storm Phoenix", "External",
     "unknown", "Advanced persistent threat actor.", True, 1),
    ("r-tamang", "Roshan Tamang", "DevOps Engineer", "r.tamang",
     "Has admin access to CI/CD pipeline.", False, 2),
    ("svc-deploy", "svc.deploy", "Service Account", "svc.deploy",
     "CI/CD deployment account — compromised.", False, 3),
    ("p-sharma", "Priya Sharma", "Finance", "p.sharma",
     "Clicked phishing link — credentials stolen.", False, 4),
]

TIMELINE = [
    ("01:15", "other", "Phishing email received by p.sharma", None),
    ("01:22", "other", "p.sharma clicks credential-harvesting link", None),
    ("02:05", "login", "VPN login from 45.33.98.12 using p.sharma creds", None),
    ("02:15", "other", "PowerShell -enc drops beacon on WS-07", None),
    ("02:30", "other", "Token impersonation — escalation to svc.deploy", None),
    ("02:45", "other", "WMI lateral movement to DC-01, FS-03", None),
    ("03:00", "other", "DNS tunneling begins — data.storm.example", None),
    ("03:30", "other", "7z compression of financial data", None),
    ("03:45", "other", "HTTPS exfil to drop.storm.example", None),
    ("04:00", "other", "Scheduled task created for persistence", None),
    ("04:30", "other", "Ransomware deployed via PsExec", None),
    ("04:35", "other", "Ransom note dropped on FS-03", None),
    ("05:00", "other", "svc.deploy password rotation (automated — FP)", None),
    ("05:15", "other", "Backup job large transfer (automated — FP)", None),
    ("05:30", "other", "Developer USB for code review (approved — FP)", None),
]

ARTIFACTS = {
    "browser_history": [
        ("01:22", {"url": "https://koshi-secure.phish.example/login",
                   "title": "Koshi Corp — Verify Account",
                   "visit_count": 1}, True),
        ("01:10", {"url": "https://mail.koshi.corp/inbox",
                   "title": "Webmail", "visit_count": 45}, False),
    ],
    "login_history": [
        ("02:05", {"username": "p.sharma", "login_at": "02:05",
                   "logout_at": "04:50", "duration": "02h 45m"}, True),
        ("08:30", {"username": "r.tamang", "login_at": "08:30",
                   "logout_at": "17:00", "duration": "08h 30m"}, False),
    ],
    "event_log": [
        ("02:05", {"event_id": 4624, "event_type": "user_login",
                   "description": "VPN logon 45.33.98.12 — p.sharma",
                   "user": "p.sharma"}, True),
        ("02:15", {"event_id": 4688, "event_type": "process_started",
                   "description": "powershell.exe -enc base64payload",
                   "user": "p.sharma"}, True),
        ("02:30", {"event_id": 4672, "event_type": "privilege_escalation",
                   "description": "Token impersonation → svc.deploy",
                   "user": "p.sharma"}, True),
        ("02:45", {"event_id": 4648, "event_type": "process_started",
                   "description": "WMI to DC-01, FS-03",
                   "user": "svc.deploy"}, True),
        ("03:30", {"event_id": 4663, "event_type": "file_modified",
                   "description": "7z.exe compressing \\\\FS-03\\Finance",
                   "user": "svc.deploy"}, True),
        ("04:30", {"event_id": 4688, "event_type": "process_started",
                   "description": "PsExec deploying locker.exe",
                   "user": "svc.deploy"}, True),
        ("05:00", {"event_id": 4724, "event_type": "password_change",
                   "description": "svc.deploy password rotated (scheduled)",
                   "user": "svc.deploy"}, False),
    ],
    "network_dns": [
        ("03:00", {"query": "aGVsbG8.data.storm.example",
                   "response_ip": "185.220.101.55",
                   "domain": "data.storm.example"}, True),
        ("03:45", {"query": "drop.storm.example",
                   "response_ip": "198.51.100.99",
                   "domain": "drop.storm.example"}, True),
    ],
    "network_https": [
        ("03:45", {"host": "drop.storm.example",
                   "sni": "drop.storm.example",
                   "bytes_sent": 15_728_640, "bytes_received": 512}, True),
        ("02:18", {"host": "c2.storm.example",
                   "sni": "c2.storm.example",
                   "bytes_sent": 4096, "bytes_received": 524288}, True),
        ("05:15", {"host": "backup.koshi.corp",
                   "sni": "backup.koshi.corp",
                   "bytes_sent": 52_428_800, "bytes_received": 1024}, False),
    ],
    "network_http": [
        ("04:31", {"method": "POST", "host": "c2.storm.example",
                   "path": "/api/ransom-complete",
                   "response_code": 200, "bytes_sent": 256}, True),
    ],
    "downloads": [
        ("03:40", {"filename": "koshi-financials.7z",
                   "url": "https://drop.storm.example/upload",
                   "size_bytes": 15_728_640}, True),
    ],
    "usb_history": [
        ("05:30", {"device_name": "SANDISK CRUZER (G:)",
                   "serial_number": "SDK-DEV-2026",
                   "connected_at": "05:30", "removed_at": "05:45"}, False),
    ],
    "recent_docs": [
        ("03:28", {"filename": "quarterly-report.xlsx",
                   "path": "\\\\FS-03\\Finance\\quarterly-report.xlsx",
                   "last_accessed_at": "03:28"}, True),
        ("03:29", {"filename": "payroll-2026.xlsx",
                   "path": "\\\\FS-03\\HR\\payroll-2026.xlsx",
                   "last_accessed_at": "03:29"}, True),
    ],
    "ioc_ip": [
        ("02:05", {"ip": "45.33.98.12", "reputation": "malicious",
                   "geo": "Unknown", "first_seen": "2026-09-10"}, True),
        ("03:00", {"ip": "185.220.101.55", "reputation": "malicious",
                   "geo": "Eastern Europe", "first_seen": "2026-08-20"}, True),
        ("05:15", {"ip": "10.0.1.50", "reputation": "internal",
                   "geo": "Internal", "first_seen": "2024-01-01"}, False),
    ],
    "ioc_domain": [
        ("01:22", {"domain": "koshi-secure.phish.example",
                   "reputation": "malicious",
                   "registrar": "darkregistrar.example",
                   "first_seen": "2026-09-12"}, True),
        ("03:00", {"domain": "data.storm.example",
                   "reputation": "malicious",
                   "registrar": "darkregistrar.example",
                   "first_seen": "2026-09-01"}, True),
    ],
    "ioc_hash": [
        ("02:15", {"sha256": "deadbeef" * 8,
                   "filename": "beacon.exe",
                   "verdict": "malicious",
                   "first_seen": "2026-09-14"}, True),
        ("04:30", {"sha256": "cafebabe" * 8,
                   "filename": "locker.exe",
                   "verdict": "malicious",
                   "first_seen": "2026-09-15"}, True),
    ],
    "ioc_scheduled_task": [
        ("04:00", {"name": "KoshiUpdater",
                   "command": "C:\\ProgramData\\svc-update.exe",
                   "trigger": "Every 30 minutes",
                   "user": "SYSTEM"}, True),
    ],
}

# 8 alerts — 5 real, 3 false positives.
ALERTS = [
    ("ASSESS-001", "Credential Theft — Phishing Campaign",
     "multiple_failed_logins", "critical", "confirmed",
     "Phishing email led to stolen VPN credentials for p.sharma."),
    ("ASSESS-002", "Malware Infection — Cobalt Strike Beacon",
     "possible_malware", "critical", "confirmed",
     "PowerShell -enc dropped a Cobalt Strike beacon on WS-07."),
    ("ASSESS-003", "DNS Tunnelling — Data Exfiltration Channel",
     "dns_tunneling", "critical", "confirmed",
     "Encoded TXT queries to data.storm.example — DNS exfil channel."),
    ("ASSESS-004", "Ransomware Deployment — PsExec",
     "data_exfiltration", "critical", "confirmed",
     "locker.exe deployed via PsExec — files encrypted on FS-03."),
    ("ASSESS-005", "Large HTTPS Upload — Financial Data",
     "suspicious_http_traffic", "high", "confirmed",
     "15 MB archive uploaded to drop.storm.example."),
    ("ASSESS-FP1", "Service Account Password Rotation",
     "multiple_failed_logins", "low", "false_positive",
     "svc.deploy password rotated per scheduled policy."),
    ("ASSESS-FP2", "Large Transfer — Backup Job",
     "suspicious_http_traffic", "low", "false_positive",
     "50 MB transfer to backup.koshi.corp — weekly backup."),
    ("ASSESS-FP3", "USB Device — Developer Code Review",
     "usb_activity", "low", "false_positive",
     "Approved SANDISK CRUZER used by r.tamang for code review."),
]

EXPECTED_CLASSIFICATIONS = {a[0]: a[4] for a in ALERTS}

# IR decisions for the assessment.
IR_SCENARIO = {
    "incident_type": "coordinated_apt",
    "classifications": EXPECTED_CLASSIFICATIONS,
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

MITRE_MAPPING = [
    {"tactic": "initial_access", "technique_id": "T1566.001",
     "technique_name": "Spearphishing Attachment"},
    {"tactic": "execution", "technique_id": "T1059.001",
     "technique_name": "PowerShell"},
    {"tactic": "persistence", "technique_id": "T1053.005",
     "technique_name": "Scheduled Task"},
    {"tactic": "privilege_escalation", "technique_id": "T1134.001",
     "technique_name": "Token Impersonation"},
    {"tactic": "lateral_movement", "technique_id": "T1021.006",
     "technique_name": "Windows Remote Management"},
    {"tactic": "collection", "technique_id": "T1560.001",
     "technique_name": "Archive via Utility"},
    {"tactic": "exfiltration", "technique_id": "T1048.003",
     "technique_name": "Exfiltration Over DNS"},
    {"tactic": "exfiltration", "technique_id": "T1041",
     "technique_name": "Exfiltration Over C2"},
    {"tactic": "impact", "technique_id": "T1486",
     "technique_name": "Data Encrypted for Impact"},
]

# 8 objectives — minimal guidance (no step-by-step checklist).
OBJECTIVES = [
    ("Classify every alert",
     "Determine whether each of the 8 alerts is a real incident "
     "or a false positive.",
     "state_flag", {"path": "classifications", "min_length": 5},
     ["8 alerts are in the queue — 5 real, 3 false positives.",
      "Read every alert description carefully.",
      "Low-severity automated events are likely false positives."], 80),
    ("Correctly identify false positives",
     "Mark the 3 false positives without misclassifying real incidents.",
     "state_flag", {"path": "classifications", "min_length": 8},
     ["Service account rotation is a scheduled operation.",
      "Backup jobs are expected large transfers.",
      "Approved USB devices for code review are legitimate."], 80),
    ("Search telemetry for IOCs",
     "Use the search engine to find indicators of compromise.",
     "event_emitted", {"event": "hunt_evidence_found"},
     ["Search for suspicious IPs, domains, or filenames.",
      "IOC artifacts are highlighted in the results.",
      "Cross-reference DNS queries with HTTPS destinations."], 80),
    ("Map MITRE ATT&CK techniques",
     "Tag the attack techniques used in this campaign.",
     "state_flag", {"path": "hunt_mitre_mapped", "min_length": 5},
     ["The attack uses phishing, PowerShell, privilege escalation.",
      "Also covers lateral movement, exfiltration, ransomware.",
      "Map at least 5 techniques."], 100),
    ("Complete the IR workflow",
     "Progress through all 5 incident response phases.",
     "event_emitted", {"event": "ir_all_phases_complete"},
     ["Take correct actions in each phase.",
      "Identification → Containment → Eradication → Recovery → "
      "Lessons Learned.",
      "Wrong actions reduce your score."], 100),
    ("Contain the attack",
     "Disconnect compromised hosts, block C2, revoke credentials.",
     "event_emitted", {"event": "ir_correct_action"},
     ["Block 45.33.98.12 and all storm.example domains.",
      "Revoke p.sharma and svc.deploy credentials.",
      "Isolate the compromised network segment."], 80),
    ("Recover systems",
     "Restore from backup, rotate credentials, patch.",
     "event_emitted", {"event": "ir_phase_completed"},
     ["Restore encrypted files from clean backups.",
      "Reset all compromised passwords.",
      "Patch the vulnerability that enabled token impersonation."], 80),
    ("Submit the executive report",
     "Write a comprehensive report (200+ chars). Your grade depends "
     "on everything — classifications, evidence, MITRE, decisions.",
     "event_emitted", {"event": "assessment_submitted"},
     ["Cover timeline, evidence, root cause, containment, recovery.",
      "Mention false positives you identified.",
      "Include MITRE ATT&CK technique references."], 150),
]


def _upsert_case() -> ForensicsCase:
    case = ForensicsCase.query.filter_by(lab_slug=CASE_LAB_SLUG).first()
    if case is None:
        case = ForensicsCase(lab_slug=CASE_LAB_SLUG)
        db.session.add(case)
    case.title = CASE_TITLE
    case.briefing = CASE_BRIEFING
    case.workstation_name = "DC-01 / FS-03 / WS-07"
    case.investigator = "Lead Analyst"
    case.mode = "advanced"
    db.session.flush()

    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    ForensicsSuspect.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for row in EVIDENCE:
        (slug, kind, fn, ext, owner, size, cr, mod,
         notes, susp, mf, order) = row
        db.session.add(ForensicsEvidence(
            case_id=case.id, slug=slug, kind=kind, filename=fn,
            extension=ext, owner=owner, size_bytes=size,
            created_at_display=cr, modified_at_display=mod,
            notes=notes, is_suspicious=susp,
            is_modified=mf, display_order=order))
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
    return case


def _upsert_alerts(case: ForensicsCase) -> int:
    for (code, title, atype, sev, expected_cls, desc) in ALERTS:
        alert = SocAlert.query.filter_by(alert_code=code).first()
        if alert is None:
            alert = SocAlert(alert_code=code)
            db.session.add(alert)
        alert.title = title
        alert.alert_type = atype
        alert.severity = sev
        alert.status = "open"
        alert.source = "SIEM + EDR + NDR"
        alert.at_time = "2026-09-15"
        alert.description = desc
        alert.expected_classification = expected_cls
        alert.expected_root_cause = "apt phishing credential theft"
        alert.case_id = case.id if expected_cls == "confirmed" else None
    scenario_registry.register(PRIMARY_ALERT, IR_SCENARIO)
    from app.simulators.soc import hunt_engine
    hunt_engine.register_mitre(PRIMARY_ALERT, MITRE_MAPPING)
    return len(ALERTS)


def _upsert_lab(category: LabCategory) -> Lab:
    lab = Lab.query.filter_by(slug=LAB_SLUG).first()
    if lab is None:
        lab = Lab(slug=LAB_SLUG)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = "Blue Team Assessment"
    lab.description = (
        "Final certification assessment — investigate an enterprise "
        "environment with multiple incidents and false positives. "
        "No guided workflow. Your grade determines your certification.")
    lab.difficulty = "Expert"
    lab.estimated_minutes = 105
    lab.xp_reward = 750
    lab.display_order = 100
    lab.is_active = True
    lab.simulator_key = "soc"
    lab.is_interactive = True
    prerequisite = Lab.query.filter_by(
        slug="soc-capstone-black-phoenix").first()
    lab.prerequisite_lab_id = prerequisite.id if prerequisite else None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(OBJECTIVES, start=1):
        obj = LabObjective.query.filter_by(
            lab_id=lab.id, title=title).first()
        if obj is None:
            obj = LabObjective(lab_id=lab.id, title=title)
            db.session.add(obj)
        obj.description = instruction
        obj.instruction = instruction
        obj.display_order = order
        obj.validator_type = vtype
        obj.set_validator_data(vdata)
        obj.hint1 = hints[0] if len(hints) > 0 else None
        obj.hint2 = hints[1] if len(hints) > 1 else None
        obj.hint3 = hints[2] if len(hints) > 2 else None
        obj.xp_reward = xp
        obj.is_optional = False
    return lab


def _upsert_achievement() -> None:
    a = Achievement.query.filter_by(title="Blue Team Expert").first()
    if a is None:
        a = Achievement(title="Blue Team Expert")
        db.session.add(a)
    a.description = "Passed the Blue Team certification assessment."
    a.icon = "🛡"
    a.category = "soc"
    a.condition_type = "soc_lab_completed"
    a.condition_value = 16
    a.bonus_xp = 300
    a.is_active = True
    a.display_order = 100


def _upsert_certificate() -> None:
    cert = Certificate.query.filter_by(
        slug="blue-team-analyst").first()
    if cert is None:
        cert = Certificate(slug="blue-team-analyst")
        db.session.add(cert)
    cert.title = "Blue Team Analyst"
    cert.description = (
        "Certified Blue Team Analyst — passed the enterprise "
        "investigation assessment with a grade of Pass or higher.")
    cert.category = "soc"
    cert.certificate_type = "certification"
    cert.icon = "shield"
    cert.required_labs = LAB_SLUG
    cert.required_xp = 0
    cert.is_active = True
    cert.display_order = 20


def seed_blue_team_assessment() -> dict[str, int]:
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
    result["alerts"] = _upsert_alerts(case)
    _upsert_lab(category)
    result["labs"] = 1
    result["objectives"] = len(OBJECTIVES)
    _upsert_achievement()
    result["achievements"] = 1
    _upsert_certificate()
    result["certificates"] = 1
    db.session.commit()
    return result
