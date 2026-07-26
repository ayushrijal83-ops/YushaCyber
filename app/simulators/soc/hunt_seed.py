"""Threat Hunting scenarios seed (YC-030.6). Idempotent.

Six proactive hunt scenarios. Each seeds a ForensicsCase with
IOC-typed artifacts + standard evidence artifacts, registers
MITRE ATT&CK mappings, and creates a Lab (+250 XP, Expert).

Threat Hunter achievement (+150 bonus XP) fires after all 6 hunts.
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
from app.simulators.soc import hunt_engine, scenario_registry
from app.simulators.soc.models import SocAlert

HUNTS = [
    # ------------------------------------------------------------------
    # 1. PowerShell Persistence
    # ------------------------------------------------------------------
    {
        "slug": "soc-hunt-powershell",
        "case_slug": "hunt-powershell-case",
        "title": "Hunt: PowerShell Persistence",
        "alert_code": "HUNT-001",
        "case_title": "Hunt — PowerShell Persistence",
        "case_briefing": (
            "Proactive hunt: identify PowerShell-based persistence "
            "mechanisms. Search for encoded commands, profile scripts "
            "and scheduled tasks that execute PowerShell."),
        "alert_type": "suspicious_powershell",
        "severity": "high",
        "timeline": [
            ("02:00", "other", "Scheduled task runs powershell -enc", None),
            ("02:01", "other", "Beacon payload decoded and executed", None),
        ],
        "artifacts": {
            "event_log": [
                ("02:00", {"event_id": 4688, "event_type": "process_started",
                           "description": "powershell.exe -enc ZGF0YQ==",
                           "user": "SYSTEM"}, True),
            ],
            "ioc_scheduled_task": [
                ("02:00", {"name": "WindowsUpdate",
                           "command": "powershell.exe -enc ZGF0YQ==",
                           "trigger": "Daily 02:00",
                           "user": "SYSTEM"}, True),
            ],
            "ioc_registry": [
                ("01:55", {"key": "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\SvcUpdate",
                           "value": "powershell.exe -enc ZGF0YQ==",
                           "hive": "HKLM"}, True),
            ],
        },
        "mitre": [
            {"tactic": "execution", "technique_id": "T1059.001",
             "technique_name": "PowerShell"},
            {"tactic": "persistence", "technique_id": "T1053.005",
             "technique_name": "Scheduled Task"},
            {"tactic": "persistence", "technique_id": "T1547.001",
             "technique_name": "Registry Run Keys"},
        ],
        "decisions": {
            "identification": {
                "correct_actions": ["preserve_evidence", "scan_endpoints"],
                "wrong_actions": ["ignore_alert"],
            },
            "containment": {
                "correct_actions": ["quarantine_file", "disconnect_host"],
                "wrong_actions": ["ignore_alert"],
            },
            "eradication": {
                "correct_actions": ["quarantine_file", "scan_endpoints"],
                "wrong_actions": ["ignore_alert"],
            },
            "recovery": {
                "correct_actions": ["patch_vulnerability", "update_firewall_rules"],
                "wrong_actions": ["ignore_alert"],
            },
            "lessons_learned": {
                "correct_actions": ["notify_management", "enable_mfa"],
                "wrong_actions": [],
            },
        },
    },
    # ------------------------------------------------------------------
    # 2. Suspicious DNS Activity
    # ------------------------------------------------------------------
    {
        "slug": "soc-hunt-dns",
        "case_slug": "hunt-dns-case",
        "title": "Hunt: Suspicious DNS Activity",
        "alert_code": "HUNT-002",
        "case_title": "Hunt — DNS Anomalies",
        "case_briefing": (
            "Proactive hunt: identify DNS-based exfiltration or C2. "
            "Search for high-frequency TXT queries, long subdomain "
            "labels and connections to recently registered domains."),
        "alert_type": "dns_tunneling",
        "severity": "critical",
        "timeline": [
            ("23:00", "other", "DNS query rate spikes to 90 qps", None),
            ("23:30", "other", "Encoded payloads detected in queries", None),
        ],
        "artifacts": {
            "network_dns": [
                ("23:00", {"query": "aGVsbG8.exfil.example",
                           "response_ip": "198.51.100.44",
                           "domain": "exfil.example"}, True),
                ("23:30", {"query": "ZXhmaWw.exfil.example",
                           "response_ip": "198.51.100.44",
                           "domain": "exfil.example"}, True),
            ],
            "ioc_domain": [
                ("23:00", {"domain": "exfil.example",
                           "reputation": "malicious",
                           "registrar": "darkregistrar.example",
                           "first_seen": "2026-08-01"}, True),
            ],
            "ioc_ip": [
                ("23:00", {"ip": "198.51.100.44",
                           "reputation": "malicious",
                           "geo": "Unknown",
                           "first_seen": "2026-08-01"}, True),
            ],
        },
        "mitre": [
            {"tactic": "exfiltration", "technique_id": "T1048.003",
             "technique_name": "Exfiltration Over Alternative Protocol — DNS"},
            {"tactic": "execution", "technique_id": "T1059",
             "technique_name": "Command and Scripting Interpreter"},
        ],
        "decisions": {
            "identification": {"correct_actions": ["preserve_evidence"], "wrong_actions": ["ignore_alert"]},
            "containment": {"correct_actions": ["block_ip", "isolate_network_segment"], "wrong_actions": ["ignore_alert"]},
            "eradication": {"correct_actions": ["quarantine_file", "revoke_credentials"], "wrong_actions": ["ignore_alert"]},
            "recovery": {"correct_actions": ["update_firewall_rules"], "wrong_actions": ["ignore_alert"]},
            "lessons_learned": {"correct_actions": ["notify_management"], "wrong_actions": []},
        },
    },
    # ------------------------------------------------------------------
    # 3. Credential Dumping
    # ------------------------------------------------------------------
    {
        "slug": "soc-hunt-creds",
        "case_slug": "hunt-creds-case",
        "title": "Hunt: Credential Dumping",
        "alert_code": "HUNT-003",
        "case_title": "Hunt — Credential Theft",
        "case_briefing": (
            "Proactive hunt: identify credential-dumping tools and "
            "techniques — lsass.exe memory access, Mimikatz artifacts "
            "and pass-the-hash activity."),
        "alert_type": "privilege_escalation",
        "severity": "critical",
        "timeline": [
            ("03:15", "other", "procdump.exe accesses lsass.exe", None),
            ("03:20", "other", "Mimikatz-like output detected", None),
        ],
        "artifacts": {
            "event_log": [
                ("03:15", {"event_id": 4688, "event_type": "process_started",
                           "description": "procdump.exe -ma lsass.exe",
                           "user": "svc.admin"}, True),
                ("03:20", {"event_id": 4648, "event_type": "privilege_escalation",
                           "description": "Pass-the-hash logon detected",
                           "user": "svc.admin"}, True),
            ],
            "ioc_hash": [
                ("03:15", {"sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                           "filename": "procdump.exe",
                           "verdict": "suspicious",
                           "first_seen": "2026-07-20"}, True),
            ],
            "ioc_filename": [
                ("03:15", {"filename": "lsass.dmp",
                           "path": "C:\\Temp\\lsass.dmp",
                           "size_bytes": 67108864,
                           "verdict": "malicious"}, True),
            ],
        },
        "mitre": [
            {"tactic": "credential_access", "technique_id": "T1003.001",
             "technique_name": "LSASS Memory"},
            {"tactic": "credential_access", "technique_id": "T1550.002",
             "technique_name": "Pass the Hash"},
        ],
        "decisions": {
            "identification": {"correct_actions": ["preserve_evidence", "scan_endpoints"], "wrong_actions": ["ignore_alert"]},
            "containment": {"correct_actions": ["revoke_credentials", "disconnect_host"], "wrong_actions": ["ignore_alert"]},
            "eradication": {"correct_actions": ["quarantine_file", "scan_endpoints"], "wrong_actions": ["ignore_alert"]},
            "recovery": {"correct_actions": ["reset_password", "enable_mfa"], "wrong_actions": ["ignore_alert"]},
            "lessons_learned": {"correct_actions": ["notify_management", "enable_mfa"], "wrong_actions": []},
        },
    },
    # ------------------------------------------------------------------
    # 4. Lateral Movement
    # ------------------------------------------------------------------
    {
        "slug": "soc-hunt-lateral",
        "case_slug": "hunt-lateral-case",
        "title": "Hunt: Lateral Movement",
        "alert_code": "HUNT-004",
        "case_title": "Hunt — Lateral Movement",
        "case_briefing": (
            "Proactive hunt: identify lateral movement via WMI, PsExec "
            "and RDP. Search for unusual authentication patterns and "
            "remote process execution."),
        "alert_type": "privilege_escalation",
        "severity": "high",
        "timeline": [
            ("04:00", "other", "WMI remote execution to DC-01", None),
            ("04:10", "other", "PsExec session to FS-02", None),
        ],
        "artifacts": {
            "event_log": [
                ("04:00", {"event_id": 4648, "event_type": "process_started",
                           "description": "WMI remote execution — target DC-01",
                           "user": "svc.admin"}, True),
                ("04:10", {"event_id": 4688, "event_type": "process_started",
                           "description": "PsExec.exe connecting to FS-02",
                           "user": "svc.admin"}, True),
            ],
            "login_history": [
                ("04:00", {"username": "svc.admin", "login_at": "04:00",
                           "logout_at": "04:30", "duration": "00h 30m"}, True),
            ],
            "ioc_service": [
                ("04:10", {"name": "PSEXESVC",
                           "binary_path": "C:\\Windows\\PSEXESVC.exe",
                           "start_type": "demand",
                           "user": "LocalSystem"}, True),
            ],
        },
        "mitre": [
            {"tactic": "lateral_movement", "technique_id": "T1021.006",
             "technique_name": "Windows Remote Management (WMI)"},
            {"tactic": "lateral_movement", "technique_id": "T1570",
             "technique_name": "Lateral Tool Transfer (PsExec)"},
        ],
        "decisions": {
            "identification": {"correct_actions": ["preserve_evidence", "scan_endpoints"], "wrong_actions": ["ignore_alert"]},
            "containment": {"correct_actions": ["disconnect_host", "isolate_network_segment"], "wrong_actions": ["ignore_alert"]},
            "eradication": {"correct_actions": ["revoke_credentials", "quarantine_file"], "wrong_actions": ["ignore_alert"]},
            "recovery": {"correct_actions": ["reset_password", "patch_vulnerability"], "wrong_actions": ["ignore_alert"]},
            "lessons_learned": {"correct_actions": ["enable_mfa", "notify_management"], "wrong_actions": []},
        },
    },
    # ------------------------------------------------------------------
    # 5. Hidden Scheduled Task
    # ------------------------------------------------------------------
    {
        "slug": "soc-hunt-schtask",
        "case_slug": "hunt-schtask-case",
        "title": "Hunt: Hidden Scheduled Task",
        "alert_code": "HUNT-005",
        "case_title": "Hunt — Hidden Persistence",
        "case_briefing": (
            "Proactive hunt: identify hidden scheduled tasks used for "
            "persistence. Search for tasks running uncommon binaries "
            "or connecting to external hosts."),
        "alert_type": "possible_malware",
        "severity": "high",
        "timeline": [
            ("01:00", "other", "Hidden task 'SysHealthCheck' executes", None),
            ("01:01", "other", "Binary connects to C2 host", None),
        ],
        "artifacts": {
            "ioc_scheduled_task": [
                ("01:00", {"name": "SysHealthCheck",
                           "command": "C:\\ProgramData\\health.exe",
                           "trigger": "Every 30 minutes",
                           "user": "SYSTEM"}, True),
            ],
            "event_log": [
                ("01:00", {"event_id": 4698, "event_type": "scheduled_task",
                           "description": "Task 'SysHealthCheck' executed health.exe",
                           "user": "SYSTEM"}, True),
            ],
            "network_https": [
                ("01:01", {"host": "c2.hidden.example",
                           "sni": "c2.hidden.example",
                           "bytes_sent": 128, "bytes_received": 256}, True),
            ],
            "ioc_domain": [
                ("01:01", {"domain": "c2.hidden.example",
                           "reputation": "malicious",
                           "registrar": "darkregistrar.example",
                           "first_seen": "2026-07-15"}, True),
            ],
        },
        "mitre": [
            {"tactic": "persistence", "technique_id": "T1053.005",
             "technique_name": "Scheduled Task"},
            {"tactic": "defense_evasion", "technique_id": "T1036",
             "technique_name": "Masquerading"},
        ],
        "decisions": {
            "identification": {"correct_actions": ["preserve_evidence", "scan_endpoints"], "wrong_actions": ["ignore_alert"]},
            "containment": {"correct_actions": ["quarantine_file", "block_ip"], "wrong_actions": ["ignore_alert"]},
            "eradication": {"correct_actions": ["quarantine_file", "scan_endpoints"], "wrong_actions": ["ignore_alert"]},
            "recovery": {"correct_actions": ["patch_vulnerability", "update_firewall_rules"], "wrong_actions": ["ignore_alert"]},
            "lessons_learned": {"correct_actions": ["notify_management"], "wrong_actions": []},
        },
    },
    # ------------------------------------------------------------------
    # 6. Beaconing Malware
    # ------------------------------------------------------------------
    {
        "slug": "soc-hunt-beacon",
        "case_slug": "hunt-beacon-case",
        "title": "Hunt: Beaconing Malware",
        "alert_code": "HUNT-006",
        "case_title": "Hunt — C2 Beaconing",
        "case_briefing": (
            "Proactive hunt: identify malware beaconing via periodic "
            "HTTPS connections. Search for processes making regular "
            "call-home connections with consistent intervals."),
        "alert_type": "suspicious_http_traffic",
        "severity": "critical",
        "timeline": [
            ("12:00", "other", "svchost-check.exe starts", None),
            ("12:01", "other", "HTTPS beacon every 60s to c2.beacon.example", None),
        ],
        "artifacts": {
            "network_https": [
                ("12:01", {"host": "c2.beacon.example",
                           "sni": "c2.beacon.example",
                           "bytes_sent": 128, "bytes_received": 256}, True),
            ],
            "network_dns": [
                ("12:00", {"query": "c2.beacon.example",
                           "response_ip": "45.77.88.99",
                           "domain": "c2.beacon.example"}, True),
            ],
            "event_log": [
                ("12:00", {"event_id": 4688, "event_type": "process_started",
                           "description": "svchost-check.exe started",
                           "user": "SYSTEM"}, True),
            ],
            "ioc_ip": [
                ("12:00", {"ip": "45.77.88.99",
                           "reputation": "malicious",
                           "geo": "Unknown",
                           "first_seen": "2026-07-25"}, True),
            ],
            "ioc_hash": [
                ("12:00", {"sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678",
                           "filename": "svchost-check.exe",
                           "verdict": "malicious",
                           "first_seen": "2026-07-25"}, True),
            ],
        },
        "mitre": [
            {"tactic": "execution", "technique_id": "T1059",
             "technique_name": "Command and Scripting Interpreter"},
            {"tactic": "persistence", "technique_id": "T1543.003",
             "technique_name": "Windows Service"},
            {"tactic": "exfiltration", "technique_id": "T1041",
             "technique_name": "Exfiltration Over C2 Channel"},
        ],
        "decisions": {
            "identification": {"correct_actions": ["preserve_evidence", "scan_endpoints"], "wrong_actions": ["ignore_alert"]},
            "containment": {"correct_actions": ["disconnect_host", "block_ip", "quarantine_file"], "wrong_actions": ["ignore_alert"]},
            "eradication": {"correct_actions": ["quarantine_file", "scan_endpoints"], "wrong_actions": ["ignore_alert"]},
            "recovery": {"correct_actions": ["patch_vulnerability", "update_firewall_rules"], "wrong_actions": ["ignore_alert"]},
            "lessons_learned": {"correct_actions": ["enable_mfa", "notify_management", "update_firewall_rules"], "wrong_actions": []},
        },
    },
]

# Standard 6 objectives for every hunt.
def _hunt_objectives() -> list[tuple]:
    return [
        ("Search telemetry and find IOCs",
         "Use the search engine to query telemetry and identify IOCs.",
         "event_emitted", {"event": "hunt_evidence_found"},
         ["Type an IP, domain, hash or process name in the search.",
          "IOC artifacts are highlighted in the results.",
          "Every successful search counts toward your score."], 40),
        ("Bookmark key evidence",
         "Bookmark at least 3 pieces of evidence.",
         "state_flag", {"path": "hunt_bookmarks", "min_length": 3},
         ["Click the bookmark button on evidence rows.",
          "Bookmarks appear in your Investigation Notes.",
          "More bookmarks = higher evidence-usage score."], 35),
        ("Map MITRE ATT&CK techniques",
         "Tag every technique used in this hunt.",
         "event_emitted", {"event": "all_mitre_mapped"},
         ["Open the MITRE ATT&CK panel.",
          "Select the techniques that match the IOCs you found.",
          "All expected techniques must be mapped."], 40),
        ("Add structured investigation notes",
         "Write at least 2 investigation notes with observations.",
         "state_flag", {"path": "hunt_notes", "min_length": 2},
         ["Use the Add Note form.",
          "Include title, observation, evidence reference and priority.",
          "Notes demonstrate your analytical process."], 35),
        ("Complete the IR workflow",
         "Progress through all 5 IR phases with correct decisions.",
         "event_emitted", {"event": "ir_all_phases_complete"},
         ["Take correct actions in each phase.",
          "Wrong actions reduce your score.",
          "Complete all five phases before submitting."], 50),
        ("Submit the hunt report",
         "Write a professional report covering hypothesis, evidence, "
         "findings, MITRE mapping and recommendations (150+ chars).",
         "event_emitted", {"event": "hunt_report_submitted"},
         ["Cover: Executive Summary, Hypothesis, Evidence, Findings, "
          "MITRE, Recommendations.",
          "150+ characters, 3+ sections for maximum report score.",
          "Pass or better closes the hunt."], 50),
    ]


def _seed_one_hunt(hunt: dict, category: LabCategory,
                   prev_slug: str | None) -> dict:
    result = {"case": 0, "alerts": 0, "labs": 0,
              "objectives": 0, "artifacts": 0}
    slug = hunt["slug"]

    case = ForensicsCase.query.filter_by(
        lab_slug=hunt["case_slug"]).first()
    if case is None:
        case = ForensicsCase(lab_slug=hunt["case_slug"])
        db.session.add(case)
    case.title = hunt["case_title"]
    case.briefing = hunt["case_briefing"]
    case.workstation_name = "HUNT-STATION"
    case.investigator = "Threat Hunter Ayush"
    case.mode = "applied"
    db.session.flush()

    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for at_time, kind, desc, ev_slug in hunt.get("timeline") or []:
        db.session.add(ForensicsTimelineEvent(
            case_id=case.id, at_time=at_time, kind=kind,
            description=desc, evidence_slug=ev_slug))
    order = 0
    for source_type, rows in (hunt.get("artifacts") or {}).items():
        for at_time, data, is_key in rows:
            order += 1
            a = ForensicsArtifact(
                case_id=case.id, source_type=source_type,
                at_time=at_time, is_key=is_key, sort_order=order)
            a.set_data(data)
            db.session.add(a)
    result["case"] = 1
    result["artifacts"] = order

    alert = SocAlert.query.filter_by(
        alert_code=hunt["alert_code"]).first()
    if alert is None:
        alert = SocAlert(alert_code=hunt["alert_code"])
        db.session.add(alert)
    alert.title = hunt["case_title"]
    alert.alert_type = hunt["alert_type"]
    alert.severity = hunt["severity"]
    alert.status = "open"
    alert.source = "Threat Hunt"
    alert.at_time = (hunt.get("timeline") or [("", "", "", "")])[0][0]
    alert.description = hunt["case_briefing"][:500]
    alert.expected_classification = "confirmed"
    alert.expected_root_cause = hunt["alert_type"]
    alert.case_id = case.id
    result["alerts"] = 1

    # Register decisions + MITRE.
    scenario_registry.register(hunt["alert_code"], {
        "incident_type": hunt["alert_type"],
        "phases": hunt.get("decisions") or {},
    })
    hunt_engine.register_mitre(hunt["alert_code"],
                               hunt.get("mitre") or [])

    lab = Lab.query.filter_by(slug=slug).first()
    if lab is None:
        lab = Lab(slug=slug)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = hunt["title"]
    lab.description = hunt["case_briefing"][:300]
    lab.difficulty = "Expert"
    lab.estimated_minutes = 50
    lab.xp_reward = 250
    lab.display_order = 20 + HUNTS.index(hunt)
    lab.is_active = True
    lab.simulator_key = "soc"
    lab.is_interactive = True
    prerequisite = None
    if prev_slug:
        prerequisite = Lab.query.filter_by(slug=prev_slug).first()
    lab.prerequisite_lab_id = prerequisite.id if prerequisite else None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(_hunt_objectives(), start=1):
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
    result["labs"] = 1
    result["objectives"] = 6
    return result


def _upsert_hunt_achievement() -> None:
    achievement = Achievement.query.filter_by(
        title="Threat Hunter Elite").first()
    if achievement is None:
        achievement = Achievement(title="Threat Hunter Elite")
        db.session.add(achievement)
    achievement.description = (
        "Completed every Threat Hunting scenario.")
    achievement.icon = "🎯"
    achievement.category = "soc"
    achievement.condition_type = "soc_lab_completed"
    achievement.condition_value = 15  # 9 SOC + 6 hunts
    achievement.bonus_xp = 150
    achievement.is_active = True
    achievement.display_order = 97


def seed_threat_hunting() -> dict[str, int]:
    totals = {"cases": 0, "alerts": 0, "labs": 0,
              "objectives": 0, "achievements": 0}
    category = LabCategory.query.filter_by(
        slug="soc-simulator").first()
    if category is None:
        category = LabCategory(slug="soc-simulator",
                               name="Security Operations Center",
                               display_order=90, is_active=True)
        db.session.add(category)
        db.session.flush()

    prev = "soc-capstone-black-phoenix"
    for hunt in HUNTS:
        r = _seed_one_hunt(hunt, category, prev)
        for k in ("cases", "alerts", "labs", "objectives"):
            totals[k] = totals.get(k, 0) + r.get(k, r.get("case", 0))
        prev = hunt["slug"]

    _upsert_hunt_achievement()
    totals["achievements"] = 1
    db.session.commit()
    return totals
