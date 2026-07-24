"""SOC Analyst Simulator seed (YC-030.1). Idempotent.

Seeds:
  · SOC playbooks — one per alert_type, 5 phases each (Identification →
    Lessons Learned).
  · SOC alerts — 8 alerts populating the queue. Only ALERT-2026-0007
    (Data Exfiltration, Critical) is wired to a forensics case (we
    reuse the Applied lab's Insider Exfil case). The rest are queue
    dressing so the dashboard shows realistic numbers.
  · Roadmap category "Security Operations Center".
  · Lab "soc-analyst-fundamentals" (Medium, +150 XP, 6 objectives).
  · Achievement "SOC Rookie" (+50 bonus XP, first SOC lab completion).
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.forensics.models import ForensicsCase
from app.labs.models import Lab, LabCategory, LabObjective, SimulatorEngine
from app.roadmap.models import RoadmapCategory
from app.simulators.soc.models import (
    SocAlert,
    SocChecklistItem,
    SocPlaybook,
    SocPlaybookStep,
)

# ---------------------------------------------------------------------------
# Playbooks — 5 phases each.
# ---------------------------------------------------------------------------
# (alert_type, title, summary, phase steps dict)
PLAYBOOKS = {
    "data_exfiltration": {
        "title": "Data Exfiltration Response",
        "summary": ("Suspected unauthorised movement of sensitive data "
                    "out of the corporate network."),
        "steps": [
            ("identification", "Confirm exfiltration channel",
             "Correlate DNS + HTTP/HTTPS + endpoint logs to prove data "
             "left the network. Identify hostname, protocol, volume."),
            ("identification", "Attribute the source",
             "Match the outbound session to an internal endpoint and "
             "user account (event log 4624 → session id → workstation)."),
            ("containment", "Block outbound destination",
             "Add the destination hostname / IP to the egress deny list "
             "on the firewall and proxy."),
            ("containment", "Suspend the compromised account",
             "Disable the account, expire tokens, force re-auth."),
            ("eradication", "Remove exfiltration artefacts",
             "Delete any staged archives, uploader binaries and browser "
             "cache remnants from the endpoint."),
            ("recovery", "Rotate credentials + reissue endpoint",
             "Reset the user's password + MFA, re-image the endpoint."),
            ("lessons_learned", "Update DLP + egress policy",
             "Add the destination + traffic pattern to DLP rules; "
             "review who else could reach it."),
        ],
    },
    "multiple_failed_logins": {
        "title": "Brute-Force / Credential Spray Response",
        "summary": ("High volume of failed authentication attempts "
                    "against one or more accounts."),
        "steps": [
            ("identification", "Confirm brute-force pattern",
             "Look at event log 4625 counts + source IPs over time."),
            ("identification", "Determine target scope",
             "One account or many? External or internal source?"),
            ("containment", "Rate-limit / block source",
             "Add source IP(s) to the deny list; enable adaptive MFA "
             "for the targeted account."),
            ("containment", "Force password rotation",
             "For any account that eventually authenticated."),
            ("eradication", "Kill live sessions",
             "Invalidate all active sessions for the targeted account."),
            ("recovery", "Re-enable account with monitoring",
             "Watch subsequent logons for the next 24 hours."),
            ("lessons_learned", "Tune lockout policy",
             "Adjust threshold + duration; ensure MFA is enforced."),
        ],
    },
    "suspicious_powershell": {
        "title": "Suspicious PowerShell Activity",
        "summary": ("Encoded or downloader PowerShell command observed "
                    "on an endpoint."),
        "steps": [
            ("identification", "Capture the command line",
             "Extract the full command from event log 4104 / EDR."),
            ("identification", "Sandbox the payload",
             "Detonate the resolved URL / decoded script in a sandbox."),
            ("containment", "Isolate the endpoint",
             "Network-quarantine the affected host."),
            ("eradication", "Remove persistence",
             "Kill scheduled tasks, registry Run keys and services "
             "the payload installed."),
            ("recovery", "Rebuild endpoint",
             "Re-image the workstation from a golden image."),
            ("lessons_learned", "Block command family",
             "Add hashes + URLs to EDR block list; publish detection."),
        ],
    },
    "possible_malware": {
        "title": "Endpoint Malware Response",
        "summary": ("EDR flagged a suspicious binary or memory pattern."),
        "steps": [
            ("identification", "Confirm the detection",
             "Cross-check EDR alert with process tree + network."),
            ("containment", "Isolate the endpoint",
             "Cut off network access while investigating."),
            ("eradication", "Remove the binary and persistence",
             "Kill running processes, delete artefacts, remove "
             "persistence mechanisms."),
            ("recovery", "Restore from clean state",
             "Re-image or restore from a known-good snapshot."),
            ("lessons_learned", "Publish IOCs",
             "Push file hashes + C2 domains to the platform block list."),
        ],
    },
    "dns_tunneling": {
        "title": "DNS Tunneling / Covert Channel",
        "summary": ("Unusually long or high-entropy DNS queries "
                    "suggesting a covert channel."),
        "steps": [
            ("identification", "Confirm tunneling pattern",
             "Look at DNS query length distribution + response types."),
            ("containment", "Blackhole the domain",
             "Sinkhole the parent domain in the resolver."),
            ("eradication", "Remove endpoint agent",
             "Kill the process using the DNS resolver."),
            ("recovery", "Rotate DNS resolver credentials",
             "If your resolver is TSIG-authenticated."),
            ("lessons_learned", "Tune DNS analytics",
             "Add the pattern to your DNS anomaly detection."),
        ],
    },
    "suspicious_http_traffic": {
        "title": "Suspicious HTTP Traffic",
        "summary": ("Unexpected HTTP traffic pattern — beacons, "
                    "large uploads, or unusual user-agents."),
        "steps": [
            ("identification", "Characterise the traffic",
             "Look at request cadence, size distribution, user-agent."),
            ("containment", "Block destination + UA",
             "Add both destination and user-agent to the proxy block "
             "list."),
            ("eradication", "Remove the endpoint client",
             "Identify the process generating the traffic; remove it."),
            ("recovery", "Re-image endpoint",
             "Restore from a clean snapshot."),
            ("lessons_learned", "Tune HTTP anomaly rules",
             "Publish the pattern to your web-proxy analytics."),
        ],
    },
    "usb_activity": {
        "title": "Removable Media / USB Activity",
        "summary": ("A USB device was connected outside policy."),
        "steps": [
            ("identification", "Identify device + user",
             "Serial + vendor from event log; correlate to session."),
            ("containment", "Block device class",
             "Disable USB mass storage via GPO for the affected asset."),
            ("eradication", "Remove copied data",
             "If exfil suspected: contain the destination as data-loss."),
            ("recovery", "Enforce approved-device list",
             "Ensure the removable-media policy is in force."),
            ("lessons_learned", "Review USB policy",
             "Update the approved-device list; enable USB analytics."),
        ],
    },
    "privilege_escalation": {
        "title": "Privilege Escalation",
        "summary": ("An account gained privileges it shouldn't have."),
        "steps": [
            ("identification", "Confirm the escalation path",
             "Which group / role was joined? By whom? Which endpoint?"),
            ("containment", "Reverse the change",
             "Remove the account from the elevated group."),
            ("eradication", "Kill sessions",
             "Invalidate active tokens; force re-auth."),
            ("recovery", "Rotate secrets",
             "Reset the account's password + rotate any secrets it "
             "may have touched."),
            ("lessons_learned", "Review group hygiene",
             "Audit membership + change approvals for that group."),
        ],
    },
}


# ---------------------------------------------------------------------------
# Alerts — 8 alerts populating the queue.
# ---------------------------------------------------------------------------
# (alert_code, title, alert_type, severity, status, source, at_time,
#  description, wire_to_applied_case)
ALERTS = [
    ("ALERT-2026-0001", "Multiple failed logons — s.kc",
     "multiple_failed_logins", "medium", "resolved",
     "SIEM · Windows Event 4625", "2026-05-10 03:12",
     "45 failed logon attempts against s.kc from a single external IP. "
     "Auto-lockout triggered; source blocked at the firewall.",
     False),
    ("ALERT-2026-0002", "Encoded PowerShell on WKS-14",
     "suspicious_powershell", "high", "open",
     "EDR · CrowdStrike", "2026-05-11 10:04",
     "Base64-encoded PowerShell command observed on WKS-14. Command "
     "resolves to a downloader targeting a raw pastebin URL.",
     False),
    ("ALERT-2026-0003", "USB device outside policy",
     "usb_activity", "medium", "open",
     "Endpoint · DLP agent", "2026-05-11 14:22",
     "TOSHIBA-USB (serial TSH-8811-A3) connected on WKS-07 — not on "
     "the approved-device list.",
     False),
    ("ALERT-2026-0004", "DNS lookups to newly-observed TLD",
     "dns_tunneling", "medium", "in_progress",
     "SIEM · Resolver logs", "2026-05-12 09:15",
     "High entropy subdomains under evil.example; possible DNS "
     "tunneling.",
     False),
    ("ALERT-2026-0005", "EDR flagged process on WKS-03",
     "possible_malware", "high", "resolved",
     "EDR · SentinelOne", "2026-05-09 22:41",
     "Suspicious loader launched under user context. Endpoint "
     "re-imaged. IOCs published.",
     False),
    ("ALERT-2026-0006", "HTTPS beacon to filedump.example",
     "suspicious_http_traffic", "high", "in_progress",
     "Proxy · Squid access logs", "2026-05-14 22:26",
     "Repeated small POSTs from d.moktan → filedump.example. Pattern "
     "consistent with a covert uploader.",
     False),
    ("ALERT-2026-0007",
     "Data exfiltration — large HTTPS upload to filedump.example",
     "data_exfiltration", "critical", "open",
     "SIEM · Proxy + DLP", "2026-05-11 22:34",
     "1.2 MB HTTPS upload from s.kc → filedump.example correlated "
     "with a roadmap-2026.pdf access and a preceding DNS lookup to "
     "the same host. Suspect insider credential misuse. INVESTIGATE.",
     True),   # wired to the advanced Corporate Data Leak case
    ("ALERT-2026-0008", "Privilege escalation — admin group joined",
     "privilege_escalation", "high", "closed",
     "IdP · Okta", "2026-05-08 18:52",
     "s.kc was added to Domain Admins outside change window. Change "
     "reverted; audit completed.",
     False),
]


CHECKLIST = [
    ("open-alert",          "Open the alert",                            True,  1),
    ("review-timeline",     "Review the unified workstation timeline",   True,  2),
    ("review-network",      "Review network evidence (DNS + HTTPS)",     True,  3),
    ("identify-account",    "Identify the compromised account",          True,  4),
    ("attach-playbook",     "Attach the correct playbook",               True,  5),
    ("state-root-cause",    "State the root cause",                      True,  6),
    ("close-with-report",   "Close the alert with a full report",        True,  7),
]


# ---------------------------------------------------------------------------
# Objectives — 6 tasks.
# ---------------------------------------------------------------------------
OBJECTIVES = [
    ("Triage the alert queue",
     "Open ALERT-2026-0007 in the queue.",
     "event_emitted",
     {"event": "alert_opened"},
     ["The critical alert is at the top of the queue.",
      "It's tagged Data Exfiltration.",
      "Click its Open button."],
     20),
    ("Investigate the evidence",
     "Review the network evidence — open the DNS and HTTPS viewers.",
     "event_emitted",
     {"event": "source_opened"},
     ["The evidence panel exposes every source tab.",
      "Look for DNS Requests and HTTPS Sessions.",
      "Click each to load its viewer."],
     20),
    ("Attach the correct playbook",
     "Pick the playbook whose alert_type matches this incident.",
     "event_emitted",
     {"event": "correct_playbook_selected"},
     ["The alert is a Data Exfiltration case.",
      "The playbook dropdown lists every alert_type.",
      "Pick 'data_exfiltration'."],
     30),
    ("State the root cause",
     "Write a root-cause sentence that names the exfiltration channel.",
     "event_emitted",
     {"event": "root_cause_named"},
     ["Root-cause statements should name what left the network and how.",
      "Include a word from the family: exfil / leak / upload / "
      "insider / credential.",
      "Example: 'Insider credential misuse — HTTPS exfil.'"],
     25),
    ("Complete the response checklist",
     "Tick every required item on the SOC checklist.",
     "event_emitted",
     {"event": "checklist_complete"},
     ["The checklist has 7 items on the right side of the workspace.",
      "Each item corresponds to a step of the investigation.",
      "Tick them all before closing."],
     25),
    ("Close the incident",
     "Submit a final report and close the alert.",
     "event_emitted",
     {"event": "incident_closed"},
     ["Your final report needs to be at least 120 characters.",
      "Touch at least three sections: Summary, Timeline, Evidence, "
      "Root Cause, Actions, Recommendations.",
      "All prior checks must pass simultaneously."],
     30),
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------
def _upsert_playbooks() -> int:
    count = 0
    for alert_type, spec in PLAYBOOKS.items():
        playbook = SocPlaybook.query.filter_by(
            alert_type=alert_type).first()
        if playbook is None:
            playbook = SocPlaybook(alert_type=alert_type)
            db.session.add(playbook)
        playbook.title = spec["title"]
        playbook.summary = spec["summary"]
        db.session.flush()
        SocPlaybookStep.query.filter_by(playbook_id=playbook.id).delete()
        db.session.flush()
        for order, (phase, title, body) in enumerate(spec["steps"],
                                                     start=1):
            db.session.add(SocPlaybookStep(
                playbook_id=playbook.id, phase=phase,
                title=title, body=body, display_order=order))
        count += 1
    return count


def _upsert_alerts() -> int:
    """Seed 8 alerts. The critical exfil alert is wired to the
    Applied lab's Insider Exfil case so the analyst sees a fully
    populated investigation workspace."""
    applied_case = ForensicsCase.query.filter_by(
        lab_slug="forensics-advanced").first()
    case_id = applied_case.id if applied_case else None

    count = 0
    for (code, title, alert_type, severity, status, source,
         at_time, description, wire_to_case) in ALERTS:
        alert = SocAlert.query.filter_by(alert_code=code).first()
        if alert is None:
            alert = SocAlert(alert_code=code)
            db.session.add(alert)
        alert.title = title
        alert.alert_type = alert_type
        alert.severity = severity
        alert.status = status
        alert.source = source
        alert.at_time = at_time
        alert.description = description
        alert.case_id = case_id if wire_to_case else None
        count += 1
    return count


def _upsert_checklist(case_id: int | None) -> int:
    """Seed the SOC checklist on the linked forensics case."""
    if case_id is None:
        return 0
    SocChecklistItem.query.filter_by(case_id=case_id).delete()
    db.session.flush()
    for slug, text, required, order in CHECKLIST:
        db.session.add(SocChecklistItem(
            case_id=case_id, slug=slug, text=text,
            is_required=required, display_order=order))
    return len(CHECKLIST)


def _upsert_roadmap_category() -> None:
    category = RoadmapCategory.query.filter_by(title="Security Operations Center").first()
    if category is None:
        category = RoadmapCategory(title="Security Operations Center")
        db.session.add(category)
    category.description = (
        "Analyst-driven investigation of security alerts — dashboards, "
        "queues, playbooks and incident reports built on top of the "
        "Digital Forensics engines.")
    category.icon = "shield"
    category.color = "#00d4aa"
    category.display_order = 85
    category.is_active = True


def _upsert_soc_lab(prerequisite_slug: str | None) -> Lab:
    # SOC labs live in a lab-category too (Lab.category_id is
    # required). Create a dedicated "SOC Simulator" LabCategory
    # separate from the roadmap so labs render on the Labs index.
    category = LabCategory.query.filter_by(slug="soc-simulator").first()
    if category is None:
        category = LabCategory(slug="soc-simulator")
        db.session.add(category)
    category.name = "SOC Analyst Simulator"
    category.description = ("Live analyst workspace: triage the queue, "
                            "investigate alerts and close incidents.")
    category.icon = "shield"
    category.display_order = 85
    category.is_active = True
    db.session.flush()

    engine_row = SimulatorEngine.query.filter_by(key="soc").first()
    if engine_row is None:
        engine_row = SimulatorEngine(key="soc")
        db.session.add(engine_row)
    engine_row.name = "SOC Analyst Simulator"
    engine_row.description = ("Alert queue, dashboards, playbooks and "
                              "incident reports over the Digital "
                              "Forensics evidence engine.")
    engine_row.capabilities = "inspector"
    engine_row.is_active = True

    lab = Lab.query.filter_by(slug="soc-analyst-fundamentals").first()
    if lab is None:
        lab = Lab(slug="soc-analyst-fundamentals")
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = "SOC Analyst: Fundamentals"
    lab.description = (
        "Live SOC analyst workflow. Triage the alert queue, open the "
        "critical alert, correlate its evidence, attach the right "
        "playbook, and close the incident with a full report.")
    lab.difficulty = "Medium"
    lab.estimated_minutes = 40
    lab.xp_reward = 150
    lab.display_order = 1
    lab.is_active = True
    lab.simulator_key = "soc"
    lab.is_interactive = True
    prerequisite = None
    if prerequisite_slug:
        prerequisite = Lab.query.filter_by(slug=prerequisite_slug).first()
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


def _upsert_soc_achievement() -> None:
    achievement = Achievement.query.filter_by(title="SOC Rookie").first()
    if achievement is None:
        achievement = Achievement(title="SOC Rookie")
        db.session.add(achievement)
    achievement.description = (
        "Completed your first SOC Analyst investigation.")
    achievement.icon = "🛡"
    achievement.category = "soc"
    achievement.condition_type = "soc_lab_completed"
    achievement.condition_value = 1
    achievement.bonus_xp = 50
    achievement.is_active = True
    achievement.display_order = 100


def seed_soc_simulator() -> dict[str, int]:
    """Seed the whole SOC package. Idempotent."""
    result = {"playbooks": 0, "alerts": 0, "checklist": 0,
              "labs": 0, "objectives": 0, "achievements": 0}
    result["playbooks"] = _upsert_playbooks()
    result["alerts"] = _upsert_alerts()

    # Wire checklist to the advanced lab's case (the one the critical
    # alert points at).
    applied_case = ForensicsCase.query.filter_by(
        lab_slug="forensics-advanced").first()
    if applied_case is not None:
        result["checklist"] = _upsert_checklist(applied_case.id)

    _upsert_roadmap_category()
    _upsert_soc_lab(prerequisite_slug="forensics-fundamentals")
    result["labs"] = 1
    result["objectives"] = len(OBJECTIVES)
    _upsert_soc_achievement()
    result["achievements"] = 1

    db.session.commit()
    return result
