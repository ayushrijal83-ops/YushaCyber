"""Advanced SOC Scenarios seed (YC-030.4). Idempotent.

Five realistic SOC investigation scenarios. Each is just
configuration — a ForensicsCase with artifacts, a SocAlert, a
decision set (IR_SCENARIO), objectives and a lab. All ride the
existing SOC simulator (key "soc") + IR workflow + decision engine +
score engine. Zero new code paths.

Labs: soc-scenario-ransomware, soc-scenario-phishing,
      soc-scenario-insider, soc-scenario-dns-tunnel,
      soc-scenario-malware-beacon
Each: Hard, +200 XP, 6 objectives
Achievement: Threat Hunter (+150 bonus XP, soc_lab_completed >= 8)
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

# =====================================================================
# Scenario definitions — each is a self-contained dict.
# =====================================================================
SCENARIOS = [
    # ---- 1. Ransomware Attack ----
    {
        "slug": "soc-scenario-ransomware",
        "title": "SOC: Ransomware Attack",
        "case_slug": "soc-adv-ransomware-case",
        "case_title": "Case #YC-101 — Ransomware: CryptoLocker Variant",
        "case_briefing": (
            "EDR flagged suspicious PowerShell execution on "
            "WORKSTATION-31 followed by rapid file encryption. "
            "Investigate the infection vector, contain the spread, "
            "and plan recovery."),
        "alert_code": "ALERT-ADV-0001",
        "alert_title": "Ransomware — CryptoLocker Variant Detected",
        "alert_type": "possible_malware",
        "alert_severity": "critical",
        "expected_classification": "confirmed",
        "expected_root_cause": "powershell dropper ransomware",
        "evidence": [
            ("ransom-note", "document", "README_DECRYPT.txt", "txt",
             "system", 1_024, "2026-08-01 04:15", "2026-08-01 04:15",
             "Ransom note.", False, False, 1),
        ],
        "timeline": [
            ("04:02", "login", "RDP session — svc.admin", None),
            ("04:05", "other", "PowerShell encoded command executed", None),
            ("04:08", "other", "File encryption begins", None),
            ("04:15", "other", "Ransom note dropped", None),
            ("04:20", "logout", "Session ended", None),
        ],
        "artifacts": {
            "event_log": [
                ("04:02", {"event_id": 4624, "event_type": "user_login",
                           "description": "RDP logon — svc.admin",
                           "user": "svc.admin"}, True),
                ("04:05", {"event_id": 4688, "event_type": "process_started",
                           "description": "powershell.exe -enc ...",
                           "user": "svc.admin"}, True),
                ("04:08", {"event_id": 4663, "event_type": "file_modified",
                           "description": "Mass file encryption *.locked",
                           "user": "svc.admin"}, True),
            ],
            "network_dns": [
                ("04:04", {"query": "c2.cryptolock.example",
                           "response_ip": "198.51.100.33",
                           "domain": "c2.cryptolock.example"}, True),
            ],
            "network_https": [
                ("04:05", {"host": "c2.cryptolock.example",
                           "sni": "c2.cryptolock.example",
                           "bytes_sent": 2_048, "bytes_received": 262_144},
                 True),
            ],
            "login_history": [
                ("04:02", {"username": "svc.admin", "login_at": "04:02",
                           "logout_at": "04:20", "duration": "00h 18m"},
                 True),
            ],
        },
        "ir_scenario": {
            "incident_type": "ransomware",
            "phases": {
                "identification": {
                    "correct_actions": ["preserve_evidence",
                                        "scan_endpoints"],
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
                    "wrong_actions": ["ignore_alert"],
                },
                "recovery": {
                    "correct_actions": ["restore_backup",
                                        "reset_password",
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
        },
        "checklist": [
            ("identify-powershell", "Identify the PowerShell dropper", True),
            ("contain-spread", "Contain lateral movement", True),
            ("eradicate-malware", "Quarantine the ransomware payload", True),
            ("recover-files", "Plan file recovery from backups", True),
            ("submit-report", "Submit the incident report", True),
        ],
    },
    # ---- 2. Phishing Campaign ----
    {
        "slug": "soc-scenario-phishing",
        "title": "SOC: Phishing Campaign",
        "case_slug": "soc-adv-phishing-case",
        "case_title": "Case #YC-102 — Credential Phishing via HR Email",
        "case_briefing": (
            "An employee reported a suspicious email pretending to be "
            "from HR. The link led to a credential-harvesting page. "
            "Determine who was compromised and contain the account."),
        "alert_code": "ALERT-ADV-0002",
        "alert_title": "Phishing — Credential Harvesting Detected",
        "alert_type": "multiple_failed_logins",
        "alert_severity": "high",
        "expected_classification": "confirmed",
        "expected_root_cause": "phishing credential harvesting",
        "evidence": [
            ("phish-email", "document", "hr-update.eml", "eml",
             "mail-server", 48_128, "2026-08-02 09:14",
             "2026-08-02 09:14",
             "Phishing email impersonating HR.", False, False, 1),
        ],
        "timeline": [
            ("09:14", "other", "Phishing email delivered to n.shrestha", None),
            ("09:22", "other", "User clicked link — browser redirect", None),
            ("09:23", "login", "Login from unusual IP 45.33.21.88", None),
            ("09:31", "other", "Password changed on portal", None),
            ("09:45", "other", "Suspicious OAuth grant created", None),
        ],
        "artifacts": {
            "browser_history": [
                ("09:22", {"url": "https://hr-update.example/login",
                           "title": "HR Portal — Login",
                           "visit_count": 1}, True),
            ],
            "login_history": [
                ("09:23", {"username": "n.shrestha",
                           "login_at": "09:23", "logout_at": "10:15",
                           "duration": "00h 52m"}, True),
            ],
            "event_log": [
                ("09:23", {"event_id": 4624, "event_type": "user_login",
                           "description": "Login from 45.33.21.88",
                           "user": "n.shrestha"}, True),
                ("09:31", {"event_id": 4724, "event_type": "password_change",
                           "description": "Password changed — n.shrestha",
                           "user": "n.shrestha"}, True),
            ],
            "network_dns": [
                ("09:21", {"query": "hr-update.example",
                           "response_ip": "45.33.21.88",
                           "domain": "hr-update.example"}, True),
            ],
        },
        "ir_scenario": {
            "incident_type": "phishing",
            "phases": {
                "identification": {
                    "correct_actions": ["preserve_evidence",
                                        "scan_endpoints"],
                    "wrong_actions": ["ignore_alert"],
                },
                "containment": {
                    "correct_actions": ["reset_password",
                                        "revoke_credentials",
                                        "block_ip"],
                    "wrong_actions": ["ignore_alert",
                                      "restore_backup"],
                },
                "eradication": {
                    "correct_actions": ["revoke_credentials",
                                        "scan_endpoints",
                                        "rotate_api_keys"],
                    "wrong_actions": ["ignore_alert"],
                },
                "recovery": {
                    "correct_actions": ["reset_password",
                                        "enable_mfa"],
                    "wrong_actions": ["ignore_alert"],
                },
                "lessons_learned": {
                    "correct_actions": ["enable_mfa",
                                        "notify_management"],
                    "wrong_actions": [],
                },
            },
        },
        "checklist": [
            ("identify-phishing-url", "Identify the phishing URL", True),
            ("identify-compromised-user", "Identify compromised user", True),
            ("contain-account", "Reset password + revoke tokens", True),
            ("block-phishing-domain", "Block the phishing domain", True),
            ("submit-report", "Submit the incident report", True),
        ],
    },
    # ---- 3. Insider Data Theft ----
    {
        "slug": "soc-scenario-insider",
        "title": "SOC: Insider Data Theft",
        "case_slug": "soc-adv-insider-case",
        "case_title": "Case #YC-103 — Insider Data Exfiltration",
        "case_briefing": (
            "DLP flagged a large file copy to a USB device after "
            "hours. The employee has tendered resignation. Determine "
            "what was stolen and preserve evidence."),
        "alert_code": "ALERT-ADV-0003",
        "alert_title": "Insider — USB Data Copy After Hours",
        "alert_type": "data_exfiltration",
        "alert_severity": "high",
        "expected_classification": "confirmed",
        "expected_root_cause": "insider usb data theft",
        "evidence": [],
        "timeline": [
            ("20:11", "login", "Session — p.gurung (badge swipe)", None),
            ("20:25", "other", "USB connected — SANDISK 64GB", None),
            ("20:32", "other", "Large file copy: clients-2026.xlsx", None),
            ("20:38", "other", "USB removed", None),
            ("20:40", "logout", "Session ended", None),
        ],
        "artifacts": {
            "usb_history": [
                ("20:25", {"device_name": "SANDISK 64GB (G:)",
                           "serial_number": "SDK-4X8Z-7712",
                           "connected_at": "20:25",
                           "removed_at": "20:38"}, True),
            ],
            "downloads": [
                ("20:32", {"filename": "clients-2026.xlsx",
                           "url": "G:\\backup\\clients-2026.xlsx",
                           "size_bytes": 15_728_640}, True),
            ],
            "recent_docs": [
                ("20:30", {"filename": "clients-2026.xlsx",
                           "path": "C:\\Users\\p.gurung\\Documents\\clients-2026.xlsx",
                           "last_accessed_at": "20:30"}, False),
            ],
            "login_history": [
                ("20:11", {"username": "p.gurung",
                           "login_at": "20:11", "logout_at": "20:40",
                           "duration": "00h 29m"}, True),
            ],
            "event_log": [
                ("20:25", {"event_id": 20003, "event_type": "usb_connected",
                           "description": "USB connected: SANDISK 64GB",
                           "user": "p.gurung"}, True),
                ("20:32", {"event_id": 4663, "event_type": "file_modified",
                           "description": "File copied to USB: clients-2026.xlsx",
                           "user": "p.gurung"}, True),
            ],
        },
        "ir_scenario": {
            "incident_type": "insider_theft",
            "phases": {
                "identification": {
                    "correct_actions": ["preserve_evidence",
                                        "scan_endpoints"],
                    "wrong_actions": ["ignore_alert"],
                },
                "containment": {
                    "correct_actions": ["disconnect_host",
                                        "revoke_credentials"],
                    "wrong_actions": ["ignore_alert",
                                      "restore_backup"],
                },
                "eradication": {
                    "correct_actions": ["revoke_credentials",
                                        "scan_endpoints"],
                    "wrong_actions": ["ignore_alert"],
                },
                "recovery": {
                    "correct_actions": ["reset_password",
                                        "notify_management"],
                    "wrong_actions": ["ignore_alert"],
                },
                "lessons_learned": {
                    "correct_actions": ["update_firewall_rules",
                                        "notify_management",
                                        "enable_mfa"],
                    "wrong_actions": [],
                },
            },
        },
        "checklist": [
            ("identify-employee", "Identify the employee", True),
            ("identify-stolen-files", "Identify stolen documents", True),
            ("identify-usb", "Identify the USB device", True),
            ("preserve-evidence", "Preserve forensic evidence", True),
            ("submit-report", "Submit the incident report", True),
        ],
    },
    # ---- 4. DNS Tunnelling ----
    {
        "slug": "soc-scenario-dns-tunnel",
        "title": "SOC: DNS Tunnelling",
        "case_slug": "soc-adv-dns-tunnel-case",
        "case_title": "Case #YC-104 — DNS Tunnelling Exfiltration",
        "case_briefing": (
            "SIEM flagged abnormal TXT query volume to an unknown "
            "domain. Encoded payloads suggest DNS tunnelling. "
            "Identify the exfiltration technique and the C2 domain."),
        "alert_code": "ALERT-ADV-0004",
        "alert_title": "DNS Tunnelling — High-Volume TXT Queries",
        "alert_type": "dns_tunneling",
        "alert_severity": "critical",
        "expected_classification": "confirmed",
        "expected_root_cause": "dns tunnel exfiltration c2",
        "evidence": [],
        "timeline": [
            ("01:30", "login", "VPN session — m.basnet", None),
            ("01:42", "other", "dns-exfil.exe started", None),
            ("01:45", "other", "TXT queries begin — *.c2tunnel.example", None),
            ("02:10", "other", "Query rate exceeds 100/min", None),
            ("02:30", "logout", "VPN session ended", None),
        ],
        "artifacts": {
            "network_dns": [
                ("01:45", {"query": "YWJj.c2tunnel.example",
                           "response_ip": "203.0.113.42",
                           "domain": "c2tunnel.example"}, True),
                ("02:10", {"query": "ZGVm.c2tunnel.example",
                           "response_ip": "203.0.113.42",
                           "domain": "c2tunnel.example"}, True),
            ],
            "event_log": [
                ("01:30", {"event_id": 4624, "event_type": "user_login",
                           "description": "VPN logon — m.basnet",
                           "user": "m.basnet"}, True),
                ("01:42", {"event_id": 4688, "event_type": "process_started",
                           "description": "dns-exfil.exe started",
                           "user": "m.basnet"}, True),
            ],
            "login_history": [
                ("01:30", {"username": "m.basnet", "login_at": "01:30",
                           "logout_at": "02:30", "duration": "01h 00m"},
                 True),
            ],
            "browser_history": [
                ("01:35", {"url": "https://github.com/mbasnet",
                           "title": "GitHub",
                           "visit_count": 3}, False),
            ],
        },
        "ir_scenario": {
            "incident_type": "dns_tunneling",
            "phases": {
                "identification": {
                    "correct_actions": ["preserve_evidence",
                                        "scan_endpoints"],
                    "wrong_actions": ["ignore_alert"],
                },
                "containment": {
                    "correct_actions": ["block_ip",
                                        "disconnect_host",
                                        "update_firewall_rules"],
                    "wrong_actions": ["ignore_alert"],
                },
                "eradication": {
                    "correct_actions": ["quarantine_file",
                                        "revoke_credentials",
                                        "scan_endpoints"],
                    "wrong_actions": ["ignore_alert"],
                },
                "recovery": {
                    "correct_actions": ["reset_password",
                                        "patch_vulnerability"],
                    "wrong_actions": ["ignore_alert"],
                },
                "lessons_learned": {
                    "correct_actions": ["update_firewall_rules",
                                        "notify_management",
                                        "enable_mfa"],
                    "wrong_actions": [],
                },
            },
        },
        "checklist": [
            ("identify-dns-domain", "Identify the C2 domain", True),
            ("identify-technique", "Identify the exfil technique", True),
            ("block-c2", "Block the C2 IP/domain", True),
            ("contain-host", "Contain the compromised host", True),
            ("submit-report", "Submit the incident report", True),
        ],
    },
    # ---- 5. Malware Beaconing ----
    {
        "slug": "soc-scenario-malware-beacon",
        "title": "SOC: Malware Beaconing",
        "case_slug": "soc-adv-beacon-case",
        "case_title": "Case #YC-105 — Persistent Malware Beacon",
        "case_briefing": (
            "NDR detected periodic HTTPS callbacks from WORKSTATION-44 "
            "to an external IP every 60 seconds. The pattern matches "
            "C2 beaconing. Determine the persistence mechanism and "
            "identify the C2 server."),
        "alert_code": "ALERT-ADV-0005",
        "alert_title": "Malware — Periodic C2 Beaconing",
        "alert_type": "suspicious_http_traffic",
        "alert_severity": "critical",
        "expected_classification": "confirmed",
        "expected_root_cause": "malware beacon c2 persistence",
        "evidence": [],
        "timeline": [
            ("03:00", "other", "First beacon observed", None),
            ("03:01", "other", "HTTPS POST 4 KB → 185.220.101.5", None),
            ("03:02", "other", "Beacon repeats (60s interval)", None),
            ("06:00", "other", "Scheduled task fires: updater.exe", None),
            ("06:01", "other", "Beacon resumes after reboot", None),
        ],
        "artifacts": {
            "network_https": [
                ("03:01", {"host": "185.220.101.5",
                           "sni": "cdn-update.example",
                           "bytes_sent": 4_096,
                           "bytes_received": 1_024}, True),
            ],
            "network_dns": [
                ("03:00", {"query": "cdn-update.example",
                           "response_ip": "185.220.101.5",
                           "domain": "cdn-update.example"}, True),
            ],
            "event_log": [
                ("06:00", {"event_id": 4698, "event_type": "scheduled_task",
                           "description": "Scheduled task created: "
                           "WindowsUpdate_svc → updater.exe",
                           "user": "SYSTEM"}, True),
                ("03:00", {"event_id": 4688, "event_type": "process_started",
                           "description": "updater.exe started",
                           "user": "SYSTEM"}, True),
            ],
            "login_history": [
                ("02:55", {"username": "SYSTEM", "login_at": "02:55",
                           "logout_at": "", "duration": "ongoing"},
                 False),
            ],
        },
        "ir_scenario": {
            "incident_type": "malware",
            "phases": {
                "identification": {
                    "correct_actions": ["preserve_evidence",
                                        "scan_endpoints"],
                    "wrong_actions": ["ignore_alert"],
                },
                "containment": {
                    "correct_actions": ["disconnect_host",
                                        "block_ip",
                                        "isolate_network_segment"],
                    "wrong_actions": ["ignore_alert"],
                },
                "eradication": {
                    "correct_actions": ["quarantine_file",
                                        "scan_endpoints"],
                    "wrong_actions": ["ignore_alert",
                                      "restore_backup"],
                },
                "recovery": {
                    "correct_actions": ["restore_backup",
                                        "patch_vulnerability",
                                        "scan_endpoints"],
                    "wrong_actions": ["ignore_alert"],
                },
                "lessons_learned": {
                    "correct_actions": ["update_firewall_rules",
                                        "notify_management"],
                    "wrong_actions": [],
                },
            },
        },
        "checklist": [
            ("identify-c2", "Identify the C2 server", True),
            ("identify-persistence", "Identify persistence mechanism", True),
            ("contain-beacon", "Block C2 communications", True),
            ("eradicate-malware", "Remove the malware + scheduled task", True),
            ("submit-report", "Submit the incident report", True),
        ],
    },
]

# Standard objectives for every scenario (same structure, same XP).
def _make_objectives(scenario_slug):
    return [
        ("Complete Identification phase",
         "Review evidence and identify the attack vector.",
         "event_emitted", {"event": "ir_phase_completed"},
         ["Open every evidence source.",
          "Study the timeline for the initial access.",
          "Click 'Complete Phase' when done."], 30),
        ("Complete Containment phase",
         "Stop the attack from spreading.",
         "event_emitted", {"event": "ir_phase_completed"},
         ["Disconnect affected hosts or block IPs.",
          "Choose the right containment actions.",
          "Wrong choices reduce your score."], 30),
        ("Complete Eradication phase",
         "Remove the threat from the environment.",
         "event_emitted", {"event": "ir_phase_completed"},
         ["Quarantine files, revoke credentials, scan.",
          "Don't ignore the alert.",
          "Click 'Complete Phase'."], 30),
        ("Complete all five IR phases",
         "Recovery and Lessons Learned must also be done.",
         "event_emitted", {"event": "ir_all_phases_complete"},
         ["Recovery: restore, reset, patch.",
          "Lessons: enable MFA, update firewall, notify management.",
          "All five phases must be marked complete."], 30),
        ("Achieve a passing score",
         "Score depends on decisions + report quality − hints.",
         "event_emitted", {"event": "ir_report_submitted"},
         ["Take correct actions in each phase.",
          "Write a 150+ char report covering 4+ sections.",
          "Minimise hint usage."], 40),
        ("Close the incident",
         "Good or Excellent rating required to close.",
         "event_emitted", {"event": "incident_closed"},
         ["A 'Needs Improvement' rating won't close it.",
          "Go back and improve your actions/report.",
          "Resubmit when ready."], 40),
    ]


# =====================================================================
# Seeder
# =====================================================================
def _upsert_scenario(scenario: dict, category: LabCategory,
                     prev_slug: str | None) -> None:
    """Seed one complete scenario (case + alert + lab + objectives)."""
    slug = scenario["slug"]

    # ---- Forensics case ----
    case = ForensicsCase.query.filter_by(
        lab_slug=scenario["case_slug"]).first()
    if case is None:
        case = ForensicsCase(lab_slug=scenario["case_slug"])
        db.session.add(case)
    case.title = scenario["case_title"]
    case.briefing = scenario["case_briefing"]
    case.workstation_name = "WORKSTATION-SOC"
    case.investigator = "Investigator Ayush"
    case.mode = "applied"
    db.session.flush()

    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for (s, kind, fn, ext, owner, size, cr, mod,
         notes, susp, mf, order) in scenario.get("evidence", []):
        db.session.add(ForensicsEvidence(
            case_id=case.id, slug=s, kind=kind, filename=fn,
            extension=ext, owner=owner, size_bytes=size,
            created_at_display=cr, modified_at_display=mod,
            notes=notes, is_suspicious=susp,
            is_modified=mf, display_order=order))
    for at_time, kind, desc, ev_slug in scenario.get("timeline", []):
        db.session.add(ForensicsTimelineEvent(
            case_id=case.id, at_time=at_time, kind=kind,
            description=desc, evidence_slug=ev_slug))
    order = 0
    for source_type, rows in scenario.get("artifacts", {}).items():
        for at_time, data, is_key in rows:
            order += 1
            a = ForensicsArtifact(
                case_id=case.id, source_type=source_type,
                at_time=at_time, is_key=is_key, sort_order=order)
            a.set_data(data)
            db.session.add(a)

    # ---- Alert ----
    alert = SocAlert.query.filter_by(
        alert_code=scenario["alert_code"]).first()
    if alert is None:
        alert = SocAlert(alert_code=scenario["alert_code"])
        db.session.add(alert)
    alert.title = scenario["alert_title"]
    alert.alert_type = scenario["alert_type"]
    alert.severity = scenario["alert_severity"]
    alert.status = "open"
    alert.source = "EDR"
    alert.at_time = (scenario.get("timeline") or [("", )])[0][0]
    alert.description = scenario["case_briefing"]
    alert.expected_classification = scenario["expected_classification"]
    alert.expected_root_cause = scenario["expected_root_cause"]
    alert.case_id = case.id

    # ---- Checklist ----
    SocChecklistItem.query.filter_by(case_id=case.id).delete()
    db.session.flush()
    for i, (chk_slug, text, required) in enumerate(
            scenario.get("checklist", []), start=1):
        db.session.add(SocChecklistItem(
            case_id=case.id, slug=chk_slug, text=text,
            is_required=required, display_order=i))

    # ---- Register decisions in the runtime registry ----
    from app.simulators.soc import scenario_registry
    ir_data = scenario.get("ir_scenario") or scenario.get("phases") or {}
    scenario_registry.register(scenario["alert_code"], ir_data)

    # ---- Lab ----
    lab = Lab.query.filter_by(slug=slug).first()
    if lab is None:
        lab = Lab(slug=slug)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = scenario["title"]
    lab.description = scenario["case_briefing"]
    lab.difficulty = "Hard"
    lab.estimated_minutes = 50
    lab.xp_reward = 200
    lab.display_order = 10 + SCENARIOS.index(scenario)
    lab.is_active = True
    lab.simulator_key = "soc"
    lab.is_interactive = True
    prerequisite = None
    if prev_slug:
        prerequisite = Lab.query.filter_by(slug=prev_slug).first()
    lab.prerequisite_lab_id = prerequisite.id if prerequisite else None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(_make_objectives(slug), start=1):
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


def _upsert_threat_hunter() -> None:
    achievement = Achievement.query.filter_by(
        title="Threat Hunter").first()
    if achievement is None:
        achievement = Achievement(title="Threat Hunter")
        db.session.add(achievement)
    achievement.description = (
        "Completed every Advanced SOC investigation scenario.")
    achievement.icon = "🏹"
    achievement.category = "soc"
    achievement.condition_type = "soc_lab_completed"
    achievement.condition_value = 8   # fundamentals + investigation + IR + 5 advanced
    achievement.bonus_xp = 150
    achievement.is_active = True
    achievement.display_order = 96


def seed_advanced_soc_scenarios() -> dict[str, int]:
    """Seed all 5 advanced scenarios. Idempotent."""
    result = {"scenarios": 0, "labs": 0, "objectives": 0,
              "achievements": 0}
    category = LabCategory.query.filter_by(
        slug="soc-simulator").first()
    if category is None:
        category = LabCategory(slug="soc-simulator",
                               name="Security Operations Center",
                               display_order=90, is_active=True)
        db.session.add(category)
        db.session.flush()

    prev_slug = "soc-incident-response"
    for scenario in SCENARIOS:
        _upsert_scenario(scenario, category, prev_slug)
        prev_slug = scenario["slug"]
        result["scenarios"] += 1
        result["labs"] += 1
        result["objectives"] += 6

    _upsert_threat_hunter()
    result["achievements"] = 1
    db.session.commit()
    return result
