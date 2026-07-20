"""Wireshark Simulator Lab seed (YC-028.0).

Three guided labs teaching packet analysis using the simulated
Wireshark viewer. Students generate traffic (ping, nmap, nslookup)
then use the wireshark command to inspect and filter captured packets.
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
    # Lab 1: Capture & Inspect
    # ------------------------------------------------------------------
    ("wireshark-basics", "Wireshark: Capture & Inspect", "Easy", 15, 180, [
        _obj("Generate network traffic",
             "Ping the web server to create packets in the capture buffer.",
             "event_emitted", {"event": "ping", "key": "reachable", "equals": True},
             ["You need traffic before Wireshark has anything to show.",
              "Select PC-1 and run `ping web-server`.",
              "This generates ICMP packets that the capture buffer records."], 35),
        _obj("Open the packet capture",
             "Run wireshark to view all captured packets.",
             "event_emitted", {"event": "wireshark", "key": "has_packets", "equals": True},
             ["After generating traffic, run `wireshark` (no arguments).",
              "You'll see a tshark-style packet list with timestamps and protocols.",
              "The capture includes both your traffic and background ARP/DNS."], 35),
        _obj("Filter by ICMP protocol",
             "Use a display filter to show only ICMP (ping) packets.",
             "event_emitted", {"event": "wireshark", "key": "filter", "equals": "icmp"},
             ["Wireshark filters let you focus on specific traffic.",
              "The syntax is `wireshark <filter>` — try a protocol name.",
              "Run `wireshark icmp` to see only ping packets."], 40),
        _obj("Filter by ARP protocol",
             "Display only the ARP traffic in the capture.",
             "event_emitted", {"event": "wireshark", "key": "filter", "equals": "arp"},
             ["ARP maps IP addresses to MAC addresses on the local network.",
              "It's one of the most common protocols in any capture.",
              "Run `wireshark arp`."], 40),
        _obj("Apply 3 different filters",
             "Experiment with at least 3 distinct display filters.",
             "state_flag", {"path": "flags.wireshark_filters", "min_length": 3},
             ["Each unique filter string counts. Try different protocols.",
              "Examples: `wireshark icmp`, `wireshark arp`, `wireshark dns`.",
              "Or try field filters like `wireshark ip.addr == 192.168.1.20`."], 30),
    ]),

    # ------------------------------------------------------------------
    # Lab 2: Protocol Analysis
    # ------------------------------------------------------------------
    ("wireshark-protocols", "Wireshark: Protocol Analysis", "Medium", 20, 220, [
        _obj("Generate DNS traffic",
             "Run nslookup to create DNS query packets.",
             "event_emitted", {"event": "nslookup", "key": "resolved", "equals": True},
             ["DNS queries happen when you resolve hostnames.",
              "Run `nslookup web-server` from PC-1.",
              "This creates UDP port 53 traffic in the capture."], 35),
        _obj("Filter for DNS packets",
             "Isolate the DNS traffic in the capture.",
             "event_emitted", {"event": "wireshark", "key": "filter", "equals": "dns"},
             ["DNS uses UDP port 53.",
              "You can filter by protocol name: `wireshark dns`.",
              "You should see the DNS query you just generated."], 40),
        _obj("Generate HTTP-related traffic",
             "Scan the web server with nmap to create TCP traffic on ports 80/443.",
             "event_emitted", {"event": "nmap", "key": "target", "equals": "web-server"},
             ["Nmap probes create TCP packets to each scanned port.",
              "Run `nmap -sV web-server` to generate traffic.",
              "This creates TCP SYN/ACK packets on ports 80 and 443."], 45),
        _obj("Filter by IP address",
             "Show only traffic involving the web server's IP.",
             "event_emitted", {"event": "wireshark", "key": "filter", "equals": "ip.addr == 192.168.1.20"},
             ["Field filters use the syntax `field == value`.",
              "The web server's IP is 192.168.1.20.",
              "Run `wireshark ip.addr == 192.168.1.20`."], 45),
        _obj("Filter by TCP port",
             "Show only traffic on port 443 (HTTPS).",
             "event_emitted", {"event": "wireshark", "key": "filter", "equals": "tcp.port == 443"},
             ["Port filters narrow to specific services.",
              "HTTPS runs on port 443.",
              "Run `wireshark tcp.port == 443`."], 55),
    ]),

    # ------------------------------------------------------------------
    # Lab 3: Advanced Analysis
    # ------------------------------------------------------------------
    ("wireshark-advanced", "Wireshark: Advanced Analysis", "Medium", 25, 260, [
        _obj("Generate multi-protocol traffic",
             "Create a rich capture by pinging, scanning, and resolving multiple hosts.",
             "state_flag", {"path": "flags.packets", "min_length": 8},
             ["Run several different commands to fill the capture buffer.",
              "Try: `ping db-server`, then `nmap -sV web-server`, then `nslookup router`.",
              "Each command adds different protocol packets to the capture."], 40),
        _obj("View capture statistics",
             "Use wireshark stats to see a protocol breakdown.",
             "event_emitted", {"event": "wireshark", "key": "action", "equals": "stats"},
             ["The stats subcommand shows a protocol summary.",
              "Run `wireshark stats`.",
              "It shows how many packets of each protocol are captured."], 40),
        _obj("Filter for TCP traffic",
             "Isolate all TCP-based traffic in the capture.",
             "event_emitted", {"event": "wireshark", "key": "filter", "equals": "tcp"},
             ["TCP is the transport protocol for HTTP, HTTPS, SSH, and more.",
              "Run `wireshark tcp`.",
              "This shows all TCP packets including HTTP and TLS."], 45),
        _obj("Filter by source IP",
             "Show only traffic originating from PC-1.",
             "event_emitted", {"event": "wireshark", "key": "filter", "equals": "ip.src == 192.168.1.10"},
             ["Source filters use `ip.src == <address>`.",
              "PC-1's IP is 192.168.1.10.",
              "Run `wireshark ip.src == 192.168.1.10`."], 45),
        _obj("Use 6 different filters total",
             "Demonstrate mastery by applying 6 unique display filters across all labs.",
             "state_flag", {"path": "flags.wireshark_filters", "min_length": 6},
             ["Each distinct filter string counts across all Wireshark labs.",
              "Try combinations: icmp, arp, dns, tcp, ip.addr, tcp.port.",
              "Field filters like `ip.dst == x` and `tcp.port == 80` each count."], 50),
        _obj("Clear and rebuild the capture",
             "Clear the buffer, generate fresh traffic, and verify with wireshark.",
             "event_emitted", {"event": "wireshark", "key": "action", "equals": "clear"},
             ["Sometimes you want a clean capture without old noise.",
              "Run `wireshark clear` to empty the buffer.",
              "Then generate new traffic and run `wireshark` again."], 40),
    ]),
]

ACHIEVEMENTS = [
    ("Packet Sniffer",
     "Complete your first Wireshark lab.",
     "cpu", "labs", "wireshark_labs_completed", 1, 100),
    ("Traffic Analyst",
     "Complete all Wireshark labs.",
     "cpu", "labs", "wireshark_labs_completed", 3, 350),
]


def seed_wireshark_labs() -> dict[str, int]:
    """Seed the 3 Wireshark labs + achievements. Idempotent."""
    if SimulatorEngine.query.filter_by(key="net-interactive").first() is None:
        db.session.add(SimulatorEngine(
            key="net-interactive",
            name="Interactive Network",
            description="Multi-device virtual network with clickable topology.",
        ))
        db.session.flush()

    category = LabCategory.query.filter_by(slug="wireshark").first()
    if category is None:
        category = LabCategory(
            slug="wireshark", name="Wireshark", icon="cpu",
            description="Learn packet analysis with a simulated Wireshark capture viewer.",
            display_order=30, is_active=True,
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
            description=f"{title} — guided packet analysis lab.",
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

    max_order = db.session.query(
        db.func.coalesce(db.func.max(Achievement.display_order), 0)
    ).scalar()
    for offset, (title, desc, icon, cat, ctype, cvalue, bonus) in \
            enumerate(ACHIEVEMENTS, start=1):
        if Achievement.query.filter_by(title=title).first() is not None:
            continue
        db.session.add(Achievement(
            title=title, description=desc, icon=icon, category=cat,
            condition_type=ctype, condition_value=cvalue, bonus_xp=bonus,
            is_active=True, display_order=max_order + offset,
        ))
        created["achievements"] += 1

    db.session.commit()
    return created
