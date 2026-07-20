"""Nmap Simulator Lab seed (YC-027.0).

Three guided labs teaching real-world Nmap enumeration using the
simulated scanner. Every objective auto-completes when the student
runs the right nmap command — validated by the ``event_emitted``
and ``state_flag`` validators against the events the ``_cmd_nmap``
handler already emits.

Reuses the existing lab/objective/achievement/XP engine unchanged.
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.models import Lab, LabCategory, LabObjective, SimulatorEngine


def _obj(title, instruction, vtype, vdata, hints, xp, optional=False):
    return {"title": title, "instruction": instruction,
            "validator_type": vtype, "validator_data": vdata,
            "hints": hints, "xp": xp, "optional": optional}


LABS = [
    # ------------------------------------------------------------------
    # Lab 1: Nmap Basics — first scan
    # ------------------------------------------------------------------
    ("nmap-basics", "Nmap: Your First Scan", "Easy", 15, 180, [
        _obj("Scan the Web Server",
             "Run a basic nmap scan against the web server to discover open ports.",
             "event_emitted", {"event": "nmap", "key": "target", "equals": "web-server"},
             ["Select PC-1 first — you scan FROM a device, not from the map.",
              "The basic syntax is `nmap <target>` — try the hostname.",
              "Run `nmap web-server`."], 35),
        _obj("Find the SSH port on the Router",
             "Scan the router and identify whether SSH (port 22) is open.",
             "event_emitted", {"event": "nmap", "key": "target", "equals": "router"},
             ["Routers often have management interfaces open.",
              "Run `nmap router` and look at the PORT column.",
              "SSH is port 22/tcp — check if it says 'open'."], 35),
        _obj("Scan a specific port",
             "Use the -p flag to scan only port 3306 on the DB server.",
             "event_emitted", {"event": "nmap", "key": "target", "equals": "db-server"},
             ["The -p flag lets you specify exact ports to scan.",
              "The syntax is `nmap -p <port> <target>`.",
              "Try `nmap -p 3306 db-server`."], 40),
        _obj("Scan 3 different hosts",
             "Build a picture of the network by scanning at least 3 devices.",
             "state_flag", {"path": "flags.nmap_targets", "min_length": 3},
             ["Each nmap scan against a different host counts.",
              "You've already scanned some — scan one more device.",
              "Try `nmap pc-2` or `nmap 192.168.1.1`."], 40),
    ]),

    # ------------------------------------------------------------------
    # Lab 2: Service & Version Detection
    # ------------------------------------------------------------------
    ("nmap-services", "Nmap: Service Enumeration", "Medium", 20, 220, [
        _obj("Detect service versions on the Web Server",
             "Use Nmap's version detection to identify exactly what software is running.",
             "event_emitted", {"event": "nmap", "key": "service_version", "equals": True},
             ["Version detection reveals the actual software behind each port.",
              "The flag is -sV (service version).",
              "Run `nmap -sV web-server`."], 45),
        _obj("Run an aggressive scan on the DB Server",
             "The -A flag combines service detection, OS detection, and more.",
             "event_emitted", {"event": "nmap", "key": "os_detected", "equals": True},
             ["Aggressive mode enables everything at once.",
              "The flag is -A (aggressive).",
              "Try `nmap -A db-server`."], 50),
        _obj("Identify the MySQL version",
             "Find the exact MySQL version running on the database server.",
             "event_emitted", {"event": "nmap", "key": "target", "equals": "db-server"},
             ["MySQL runs on port 3306 by default.",
              "Use `nmap -sV -p 3306 db-server` to probe just that port.",
              "The VERSION column shows the exact MySQL release."], 50),
        _obj("Scan with specific ports",
             "Probe only ports 80 and 443 on the web server with version detection.",
             "event_emitted", {"event": "nmap", "key": "services", "contains": "http"},
             ["You can combine -sV with -p to be surgical.",
              "The syntax is `nmap -sV -p 80,443 <target>`.",
              "Run `nmap -sV -p 80,443 web-server`."], 40),
        _obj("Scan 5 total hosts with nmap across all labs",
             "Build a comprehensive network map by scanning 5 unique targets.",
             "state_flag", {"path": "flags.nmap_targets", "min_length": 5},
             ["Each unique target you scan counts, across all nmap labs.",
              "Check which devices you haven't scanned yet.",
              "Try scanning pc-1, pc-2, or the switch."], 35),
    ]),

    # ------------------------------------------------------------------
    # Lab 3: OS Detection & Stealth Scanning
    # ------------------------------------------------------------------
    ("nmap-advanced", "Nmap: OS Detection & Stealth", "Medium", 25, 260, [
        _obj("Detect the OS on the Web Server",
             "Use Nmap's OS detection to fingerprint the web server's operating system.",
             "event_emitted", {"event": "nmap", "key": "os_detected", "equals": True},
             ["OS detection analyses how the host responds to special probes.",
              "The flag is -O (uppercase letter O, not zero).",
              "Run `nmap -O web-server`."], 45),
        _obj("Run a SYN stealth scan",
             "Use the -sS flag for a TCP SYN (half-open) scan — the classic stealth technique.",
             "event_emitted", {"event": "nmap", "key": "target", "equals": "web-server"},
             ["SYN scans never complete the TCP handshake, making them harder to log.",
              "The flag is -sS (SYN stealth).",
              "Try `nmap -sS web-server`."], 45),
        _obj("Use fast scan mode",
             "Run a fast scan (-F) against the router to quickly check top ports.",
             "event_emitted", {"event": "nmap", "key": "target", "equals": "router"},
             ["Fast mode scans fewer ports but finishes quicker.",
              "The flag is -F (fast).",
              "Try `nmap -F router`."], 40),
        _obj("Scan a host that appears down",
             "Use -Pn to scan a host even if ping discovery fails.",
             "event_emitted", {"event": "nmap", "key": "target", "equals": "pc-2"},
             ["Some hosts block ICMP pings but still have open ports.",
              "The -Pn flag skips host discovery and scans anyway.",
              "Try `nmap -Pn pc-2`."], 40),
        _obj("Combine flags for a full assessment",
             "Run a comprehensive scan: aggressive mode + SYN + timing T4.",
             "event_emitted", {"event": "nmap", "key": "os_detected", "equals": True},
             ["Real pentesters combine multiple flags for thorough scans.",
              "Try combining -A -sS -T4 against a target.",
              "Run `nmap -A -sS -T4 web-server`."], 50),
        _obj("Scan all 6 network devices with nmap",
             "Complete your network enumeration — scan every device at least once.",
             "state_flag", {"path": "flags.nmap_targets", "min_length": 6},
             ["You need to have scanned 6 unique targets across all nmap labs.",
              "Check which devices you've missed (router, switch, pc-1, pc-2, web-server, db-server).",
              "Run nmap against any device you haven't targeted yet."], 40),
    ]),
]

ACHIEVEMENTS = [
    ("Script Kiddie",
     "Complete your first Nmap scan.",
     "cpu", "labs", "nmap_labs_completed", 1, 100),
    ("Port Scanner",
     "Complete all Nmap labs.",
     "cpu", "labs", "nmap_labs_completed", 3, 350),
]


def seed_nmap_labs() -> dict[str, int]:
    """Seed the 3 Nmap labs + achievements. Idempotent."""
    # Ensure the net-interactive engine exists (shared with networking labs).
    if SimulatorEngine.query.filter_by(key="net-interactive").first() is None:
        db.session.add(SimulatorEngine(
            key="net-interactive",
            name="Interactive Network",
            description="Multi-device virtual network with clickable topology.",
        ))
        db.session.flush()

    # Create or reuse the Nmap category.
    category = LabCategory.query.filter_by(slug="nmap").first()
    if category is None:
        category = LabCategory(
            slug="nmap", name="Nmap", icon="cpu",

            description="Learn network enumeration with a simulated Nmap scanner.",
            display_order=25, is_active=True,
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
            description=f"{title} — guided Nmap enumeration lab.",
            difficulty=diff, estimated_minutes=minutes, xp_reward=xp,
            display_order=base_order + offset, is_active=True,
            simulator_key="net-interactive", is_interactive=True,
            prerequisite_lab_id=prev_lab_id,
        )
        db.session.add(lab)
        db.session.flush()
        created["labs"] += 1

        for o_order, o in enumerate(objectives, start=1):
            objective = LabObjective(
                lab_id=lab.id, title=o["title"], description=o["instruction"],
                instruction=o["instruction"], display_order=o_order,
                validator_type=o["validator_type"], xp_reward=o["xp"],
                is_optional=o["optional"],
                hint1=o["hints"][0] or None,
                hint2=o["hints"][1] or None,
                hint3=o["hints"][2] or None,
            )
            objective.set_validator_data(o["validator_data"])
            db.session.add(objective)
            created["objectives"] += 1

        prev_lab_id = lab.id

    # Achievements
    max_order = db.session.query(
        db.func.coalesce(db.func.max(Achievement.display_order), 0)
    ).scalar()
    for offset, (title, desc, icon, category_name, ctype, cvalue, bonus) in \
            enumerate(ACHIEVEMENTS, start=1):
        if Achievement.query.filter_by(title=title).first() is not None:
            continue
        db.session.add(Achievement(
            title=title, description=desc, icon=icon, category=category_name,
            condition_type=ctype, condition_value=cvalue, bonus_xp=bonus,
            is_active=True, display_order=max_order + offset,
        ))
        created["achievements"] += 1

    db.session.commit()
    return created
