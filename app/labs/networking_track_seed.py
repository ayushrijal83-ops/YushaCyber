"""Networking learning track seed (YC-013.0).

Three sequential networking labs, each an interactive terminal lab driven by
the existing Lab Engine + Network simulator plugin. All networking content
lives here (data) and in the simulator plugin (behaviour) — the engine is
untouched.

Also seeds the track's three achievements. Their unlock conditions run
through the EXISTING achievement engine (a per-category labs metric);
nothing here awards anything.

Progression: each lab's ``prerequisite_lab_id`` points at the previous lab.
Idempotent: guarded per lab slug / achievement title, so re-running never
duplicates and it composes with the earlier placeholder Networking labs.
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.models import Lab, LabCategory, LabObjective, SimulatorEngine


def _obj(title, instruction, vtype, vdata, hints, xp, optional=False):
    return {
        "title": title, "instruction": instruction,
        "validator_type": vtype, "validator_data": vdata,
        "hints": hints, "xp": xp, "optional": optional,
    }


# ---------------------------------------------------------------------------
# The three labs. (slug, title, difficulty, minutes, xp_reward, [objectives])
# Validators reuse the existing validator engine — no new validator types.
# ---------------------------------------------------------------------------
LABS = [
    ("net-basics", "Network Basics", "Easy", 20, 120, [
        _obj("Identify your host",
             "Every machine on a network has a name. Print yours. Run: hostname",
             "event_emitted", {"event": "hostname"},
             ("One-word command.", "It prints the machine's name.",
              "Type: hostname"), 15),
        _obj("Show your IP address",
             "Find your address on the network. Run: ip addr",
             "state_flag", {"path": "flags.ip_addr_shown", "equals": True},
             ("The modern tool is 'ip'.", "The object is 'addr' (or just 'a').",
              "Type: ip addr"), 20),
        _obj("Ping the gateway",
             "The gateway (192.168.1.1) is your way out of the LAN. Check "
             "it's alive. Run: ping 192.168.1.1",
             "state_flag", {"path": "flags.pinged.192_168_1_1", "equals": True},
             ("'ping HOST' tests reachability.", "The gateway is 192.168.1.1.",
              "Type: ping 192.168.1.1"), 25),
        _obj("Ping the web server",
             "There's an internal web server named server.local. Ping it by "
             "name. Run: ping server.local",
             "state_flag", {"path": "flags.pinged.server_local", "equals": True},
             ("ping accepts names, not just IPs.", "The name is server.local.",
              "Type: ping server.local"), 25),
        _obj("Resolve a domain",
             "Ask DNS what IP example.com lives at. Run: nslookup example.com",
             "event_emitted", {"event": "nslookup", "key": "domain",
                               "equals": "example.com"},
             ("'nslookup NAME' queries DNS.", "The name is example.com.",
              "Type: nslookup example.com"), 35),
    ]),

    ("net-interfaces", "Interfaces", "Easy", 20, 140, [
        _obj("Inspect interfaces (classic)",
             "See your network cards the classic way. Run: ifconfig",
             "event_emitted", {"event": "ifconfig"},
             ("The classic interface tool.", "No arguments needed.",
              "Type: ifconfig"), 40),
        _obj("Inspect interfaces (modern)",
             "Now the modern way — compare the output. Run: ip addr",
             "state_flag", {"path": "flags.ip_addr_shown", "equals": True},
             ("The 'ip' tool replaced ifconfig.", "Object 'addr' (or 'a').",
              "Type: ip addr"), 40),
        _obj("Read the routing table",
             "Where do packets go? Show the kernel routing table. Run: route",
             "event_emitted", {"event": "route"},
             ("One word.", "It prints Destination/Gateway/Genmask columns.",
              "Type: route"), 60),
    ]),

    ("net-connectivity", "Connectivity", "Medium", 25, 160, [
        _obj("Test reachability",
             "Ping any host on the network — the gateway, a server, or "
             "example.com. Run: ping <host>",
             "event_emitted", {"event": "ping", "key": "reachable",
                               "equals": True},
             ("'ping HOST'.", "Try ping server.local.",
              "Type: ping server.local"), 40),
        _obj("Trace the route",
             "See every hop between you and example.com. Run: traceroute example.com",
             "event_emitted", {"event": "traceroute", "key": "reachable",
                               "equals": True},
             ("'traceroute HOST' lists hops.",
              "Internet traffic goes through the gateway first.",
              "Type: traceroute example.com"), 70),
        _obj("Inspect the ARP cache",
             "Your machine learned MAC addresses while you pinged. Show the "
             "IP-to-MAC table. Run: arp",
             "event_emitted", {"event": "arp", "key": "populated",
                               "equals": True},
             ("Three letters.", "It maps IPs to MAC addresses.",
              "Type: arp"), 50),
    ]),
]

# (title, description, icon, category, condition_type, condition_value, bonus_xp)
ACHIEVEMENTS = [
    ("Networking Beginner", "Complete your first Networking lab.",
     "share-2", "labs", "networking_labs_completed", 1, 50),
    ("Networking Explorer", "Complete 2 Networking labs.",
     "share-2", "labs", "networking_labs_completed", 2, 100),
    ("Networking Specialist", "Complete all 3 Networking labs.",
     "award", "labs", "networking_labs_completed", 3, 200),
]


def seed_networking_track() -> dict[str, int]:
    """Seed the Networking track. Idempotent per lab slug / achievement title."""
    # Simulator catalogue row (metadata; the plugin itself lives in code).
    if SimulatorEngine.query.filter_by(key="network").first() is None:
        db.session.add(SimulatorEngine(
            key="network", name="Network Terminal",
            description="Simulated network stack over a virtual topology.",
            capabilities="terminal", is_active=True,
        ))

    # Reuse the existing Networking category (created by the base catalogue
    # seed); create it only if this is a fresh database.
    category = LabCategory.query.filter_by(slug="networking").first()
    if category is None:
        category = LabCategory(
            name="Networking", slug="networking",
            description="Practical networking labs: analysis, scanning and services.",
            icon="share-2", display_order=2, is_active=True,
        )
        db.session.add(category)
        db.session.flush()

    created = {"labs": 0, "objectives": 0, "achievements": 0}
    prev_lab_id = None

    for order, (slug, title, diff, minutes, xp, objectives) in enumerate(
        LABS, start=1
    ):
        existing = Lab.query.filter_by(slug=slug).first()
        if existing is not None:
            prev_lab_id = existing.id
            continue

        lab = Lab(
            category_id=category.id, title=title, slug=slug,
            description=f"{title} — an interactive, fully simulated networking lab.",
            difficulty=diff, estimated_minutes=minutes, xp_reward=xp,
            display_order=order, is_active=True,
            simulator_key="network", is_interactive=True,
            prerequisite_lab_id=prev_lab_id,   # sequential unlock
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

    # Track achievements — data only; the achievement engine evaluates them.
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
