"""SOC Analyst Lab seed (YC-030.0)."""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.models import Lab, LabCategory, LabObjective, SimulatorEngine


def _obj(title, instruction, vtype, vdata, hints, xp, optional=False):
    return {"title": title, "instruction": instruction,
            "validator_type": vtype, "validator_data": vdata,
            "hints": hints, "xp": xp, "optional": optional}


LABS = [
    ("soc-brute-force", "SOC: Brute Force Investigation", "Medium", 25, 280,
     [
        _obj("Review the alert queue",
             "Open the alert dashboard to understand what triggered this investigation.",
             "event_emitted", {"event": "alerts_viewed", "key": "has_alerts", "equals": True},
             ["Start by reviewing what the SIEM flagged.",
              "Run `alerts` to see all alerts.",
              "Note the severity levels and timestamps."], 35),
        _obj("Examine the Windows logs",
             "Filter logs by the Windows event source to see authentication events.",
             "event_emitted", {"event": "logs_viewed", "key": "source", "equals": "windows"},
             ["Windows logs contain login success/failure events.",
              "Run `logs windows` to filter by source.",
              "Look for Event IDs 4624 (success) and 4625 (failure)."], 35),
        _obj("Search for the attacker IP",
             "Search the logs for the suspicious source IP from the alerts.",
             "event_emitted", {"event": "search_performed", "key": "has_results", "equals": True},
             ["The alerts mention a specific source IP.",
              "Run `search 10.0.5.99` to find all related activity.",
              "Track what this IP did across all log sources."], 40),
        _obj("Build the attack timeline",
             "View the full timeline to understand the attack progression.",
             "event_emitted", {"event": "timeline_viewed"},
             ["The timeline shows events in chronological order.",
              "Run `timeline` to see the full sequence.",
              "Follow the progression from failed logins to privilege escalation."], 40),
        _obj("Investigate the compromised account",
             "Deep-dive on the account that was eventually compromised.",
             "event_emitted", {"event": "investigated", "key": "found", "equals": True},
             ["One account was successfully brute-forced.",
              "Look at which username had failed logins then a success.",
              "Run `investigate jsmith` to see all their activity."], 45),
        _obj("Submit the incident report",
             "Document your findings: attacker IP, compromised account, attack type, severity, and remediation.",
             "event_emitted", {"event": "report_submitted", "key": "correct", "equals": True},
             ["Include all key indicators in your report.",
              "Mention the attacker IP, the compromised user, the attack type.",
              "Try `report Brute force attack from 10.0.5.99 compromised jsmith. High severity. Reset password and block IP. Enable MFA.`"], 55),
    ]),

    ("soc-port-scan", "SOC: Port Scan & Data Exfiltration", "Hard", 30, 320,
     [
        _obj("Review critical alerts",
             "Filter alerts by severity to focus on the most urgent issues.",
             "event_emitted", {"event": "alerts_viewed"},
             ["Start with the most serious alerts.",
              "Run `alerts critical` to see only critical-severity alerts.",
              "Note the reverse shell and data exfiltration alerts."], 35),
        _obj("Examine firewall logs",
             "Check what the firewall recorded about the attack.",
             "event_emitted", {"event": "logs_viewed", "key": "source", "equals": "firewall"},
             ["Firewalls log network connections and IDS alerts.",
              "Run `logs firewall`.",
              "Look for the port scan detection and large data transfers."], 40),
        _obj("Search for the external attacker",
             "Find all activity from the attacking IP address.",
             "event_emitted", {"event": "search_performed", "key": "has_results", "equals": True},
             ["The alerts show an external IP conducting the attack.",
              "Run `search 203.0.113.50`.",
              "Trace the attack from scan to exploitation to exfiltration."], 45),
        _obj("Investigate the web server",
             "Deep-dive on the compromised web server.",
             "event_emitted", {"event": "investigated", "key": "found", "equals": True},
             ["The web server was the initial entry point.",
              "Run `investigate web-01` to see all events on that host.",
              "Look for the SQL injection, reverse shell, and privilege escalation."], 50),
        _obj("Use log filtering",
             "Filter logs to isolate the privilege escalation events.",
             "event_emitted", {"event": "filter_used"},
             ["Filtering narrows the view to specific criteria.",
              "Try `filter severity critical` or `filter host web-01`.",
              "Look for the privilege escalation log entry."], 45),
        _obj("Submit the incident report",
             "Document the full attack chain with all IOCs.",
             "event_emitted", {"event": "report_submitted", "key": "correct", "equals": True},
             ["This was a multi-stage attack: scan → SQLi → shell → escalation → exfiltration.",
              "Include the attacker IP, compromised systems, and remediation steps.",
              "Try `report Port scan and SQL injection from 203.0.113.50. Reverse shell on web-01, data exfiltration from db-01. Critical severity. Isolate systems, patch SQLi, deploy WAF.`"], 65),
    ]),

    ("soc-insider", "SOC: Insider Threat Investigation", "Hard", 30, 320,
     [
        _obj("Review the DLP alerts",
             "Check what the Data Loss Prevention system flagged.",
             "event_emitted", {"event": "alerts_viewed", "key": "has_alerts", "equals": True},
             ["DLP alerts indicate potential data theft.",
              "Run `alerts` to see all alerts.",
              "Note the after-hours access and large downloads."], 35),
        _obj("Check VPN logs",
             "See who connected outside business hours.",
             "event_emitted", {"event": "logs_viewed", "key": "source", "equals": "vpn"},
             ["VPN logs show remote access connections.",
              "Run `logs vpn`.",
              "After-hours VPN access is suspicious."], 40),
        _obj("Search for the employee",
             "Find all activity by the flagged user account.",
             "event_emitted", {"event": "search_performed", "key": "has_results", "equals": True},
             ["One employee name appears across multiple alerts.",
              "Run `search mthompson`.",
              "Track everything this user did."], 45),
        _obj("View the timeline",
             "Build the sequence of events from VPN login to data exfiltration.",
             "event_emitted", {"event": "timeline_viewed"},
             ["The timeline reveals the complete picture.",
              "Run `timeline`.",
              "Follow the progression: VPN → file access → USB → email."], 45),
        _obj("Review affected hosts",
             "Identify which systems the insider accessed.",
             "event_emitted", {"event": "hosts_viewed"},
             ["The insider may have touched multiple systems.",
              "Run `hosts` to see all systems with log entries.",
              "Note the file server and workstation activity."], 40),
        _obj("Submit the incident report",
             "Document your findings about the insider threat.",
             "event_emitted", {"event": "report_submitted", "key": "correct", "equals": True},
             ["This is a data theft by an insider, not an external attack.",
              "Include the user, the data accessed, and the exfiltration methods.",
              "Try `report Insider threat by mthompson. After-hours VPN from 198.51.100.22, accessed confidential financials, copied 2.3GB to USB, emailed data to personal address. High severity. Disable account, involve HR and legal, enforce DLP and USB policy.`"], 75),
    ]),
]

ACHIEVEMENTS = [
    ("Alert Responder",
     "Complete your first SOC investigation.",
     "flag", "labs", "soc_labs_completed", 1, 150),
    ("SOC Analyst",
     "Complete all SOC investigation labs.",
     "flag", "labs", "soc_labs_completed", 3, 500),
]


def seed_soc_labs() -> dict[str, int]:
    """Seed the 3 SOC labs + achievements. Idempotent."""
    if SimulatorEngine.query.filter_by(key="soc-analyst").first() is None:
        db.session.add(SimulatorEngine(
            key="soc-analyst", name="SOC Analyst Simulator",
            description="Incident investigation and log analysis.",
        ))
        db.session.flush()

    category = LabCategory.query.filter_by(slug="soc").first()
    if category is None:
        category = LabCategory(
            slug="soc", name="SOC", icon="flag",
            description="Investigate security incidents as a SOC analyst.",
            display_order=40, is_active=True,
        )
        db.session.add(category)
        db.session.flush()

    created = {"labs": 0, "objectives": 0, "achievements": 0}
    base_order = db.session.query(
        db.func.coalesce(db.func.max(Lab.display_order), 0)
    ).filter_by(category_id=category.id).scalar()
    prev_lab_id = None

    for offset, (slug, title, diff, minutes, xp, objectives) in enumerate(LABS, start=1):
        existing = Lab.query.filter_by(slug=slug).first()
        if existing is not None:
            prev_lab_id = existing.id
            continue
        lab = Lab(
            category_id=category.id, title=title, slug=slug,
            description=f"{title} — SOC incident investigation lab.",
            difficulty=diff, estimated_minutes=minutes, xp_reward=xp,
            display_order=base_order + offset, is_active=True,
            simulator_key="soc-analyst", is_interactive=True,
            prerequisite_lab_id=prev_lab_id,
        )
        db.session.add(lab); db.session.flush()
        created["labs"] += 1
        for o_order, o in enumerate(objectives, start=1):
            obj = LabObjective(
                lab_id=lab.id, title=o["title"], description=o["instruction"],
                instruction=o["instruction"], display_order=o_order,
                validator_type=o["validator_type"], xp_reward=o["xp"],
                is_optional=o["optional"],
                hint1=o["hints"][0], hint2=o["hints"][1], hint3=o["hints"][2],
            )
            obj.set_validator_data(o["validator_data"])
            db.session.add(obj)
            created["objectives"] += 1
        prev_lab_id = lab.id

    max_order = db.session.query(
        db.func.coalesce(db.func.max(Achievement.display_order), 0)).scalar()
    for offset, (title, desc, icon, cat, ctype, cvalue, bonus) in enumerate(ACHIEVEMENTS, start=1):
        if Achievement.query.filter_by(title=title).first() is not None:
            continue
        db.session.add(Achievement(title=title, description=desc, icon=icon, category=cat,
            condition_type=ctype, condition_value=cvalue, bonus_xp=bonus,
            is_active=True, display_order=max_order + offset))
        created["achievements"] += 1

    db.session.commit()
    return created
