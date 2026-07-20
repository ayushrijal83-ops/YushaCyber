"""Interactive Networking Lab seed (YC-026.0).

Data-only seed for the multi-device network simulator. Reuses:
  · The Lab / LabObjective / SimulatorEngine tables
  · The existing validator engine (event_emitted, state_flag) — no new
    validator types
  · The per-category achievement metric ``networking_labs_completed``
    established in YC-013.0 (an "Interactive Explorer" achievement is
    added to it here)
  · The XP engine (XP awards happen through the normal objective/lab
    completion pipeline — nothing about that is touched)

Idempotent per lab slug and per achievement title, so this can be
re-run safely alongside the earlier YC-013.0 seeds.
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
    # Lab 1: Explore the network topology.
    # ------------------------------------------------------------------
    ("net-explore", "Explore the Network", "Easy", 20, 140, [
        _obj("Select PC-1",
             "Click PC-1 on the map, then check its identity. Run: hostname",
             "event_emitted", {"event": "hostname", "key": "host", "equals": "pc-1"},
             ["Click the device labeled PC-1 on the topology diagram, then use the terminal.",
              "The command is `hostname` — it prints the current device's name.",
              "After clicking PC-1, the prompt should read `pc-1>`."], 25),
        _obj("Find PC-1's IP address",
             "Show PC-1's interface details. Run: ipconfig",
             "event_emitted", {"event": "ipconfig", "key": "host", "equals": "pc-1"},
             ["Make sure PC-1 is selected before running the command.",
              "`ipconfig` (or `ifconfig`) prints IP, MAC and gateway.",
              "PC-1's address is in the 192.168.1.0/24 range."], 25),
        _obj("Identify the router",
             "Switch to the Router and print its hostname.",
             "event_emitted", {"event": "hostname", "key": "host", "equals": "router"},
             ["Click the Router node on the diagram to switch to it.",
              "Then run `hostname` from its terminal.",
              "The Router sits between the Internet and the Switch."], 30),
        _obj("Find the default gateway",
             "Back on PC-1, show the routing table. Run: route",
             "event_emitted", {"event": "route", "key": "host", "equals": "pc-1"},
             ["Select PC-1 first, then run `route`.",
              "The `default` line points at the gateway.",
              "PC-1's default gateway is the Router at 192.168.1.1."], 30),
    ]),

    # ------------------------------------------------------------------
    # Lab 2: Reachability & neighbours.
    # ------------------------------------------------------------------
    ("net-reach", "Reach & Discover", "Easy", 20, 160, [
        _obj("Ping the Router from PC-1",
             "Confirm PC-1 can reach its gateway. Run: ping 192.168.1.1",
             "event_emitted", {"event": "ping", "key": "reachable", "equals": True},
             ["Click PC-1 first so the ping originates from it.",
              "`ping 192.168.1.1` targets the Router by IP.",
              "A successful ping prints `2 packets transmitted, 2 received`."], 40),
        _obj("Ping the Web Server by name",
             "Reach the web server from PC-1. Run: ping web-server",
             "event_emitted", {"event": "ping", "key": "target", "equals": "web-server"},
             ["Hostnames on the LAN resolve directly.",
              "The command is `ping web-server`.",
              "Its IP is 192.168.1.20."], 40),
        _obj("List learned neighbours",
             "Every ping adds an ARP entry. Show them. Run: arp",
             "event_emitted", {"event": "arp", "key": "populated", "equals": True},
             ["Ping something first — a fresh device has an empty ARP cache.",
              "`arp` prints the cache for the selected host.",
              "Look for the IP → MAC mapping of the peers you contacted."], 40),
        _obj("Trace the path to the DB Server",
             "See the hop path from PC-1 to the DB Server. Run: traceroute db-server",
             "event_emitted", {"event": "traceroute", "key": "target", "equals": "db-server"},
             ["Make sure PC-1 is selected.",
              "`traceroute db-server` shows each hop.",
              "You'll go via the Switch to reach 192.168.1.30."], 40),
    ]),

    # ------------------------------------------------------------------
    # Lab 3: Investigate the servers.
    # ------------------------------------------------------------------
    ("net-inspect", "Inspect the Servers", "Medium", 25, 200, [
        _obj("List services on the Web Server",
             "Switch to the Web Server, then list listening ports. Run: netstat",
             "event_emitted", {"event": "netstat", "key": "host", "equals": "web-server"},
             ["Click Web Server on the diagram.",
              "`netstat` lists what's LISTENing.",
              "You should see HTTP (80) and HTTPS (443)."], 55),
        _obj("List services on the DB Server",
             "Now switch to the DB Server and repeat. Run: netstat",
             "event_emitted", {"event": "netstat", "key": "host", "equals": "db-server"},
             ["Click DB Server on the diagram first.",
              "`netstat` shows only what's listening on THIS device.",
              "The DB server serves MySQL on 3306."], 55),
        _obj("Discover 4 hosts on the network",
             "Explore the topology — select at least 4 devices during this lab.",
             "state_flag", {"path": "flags.visited", "min_length": 4},
             ["Click each node on the map to switch to it.",
              "Every unique device you switch to counts.",
              "Router + Switch + PC-1 + Web Server = 4."], 90),
    ]),

    # ------------------------------------------------------------------
    # Lab 4: DNS & Name Resolution (YC-026.5)
    # ------------------------------------------------------------------
    ("net-dns", "DNS & Name Resolution", "Easy", 15, 160, [
        _obj("Resolve the Web Server hostname",
             "Use nslookup to find the Web Server's IP address.",
             "event_emitted", {"event": "nslookup", "key": "target", "equals": "web-server"},
             ["Select PC-1 first, then use the nslookup command.",
              "The syntax is `nslookup <hostname>`.",
              "Try `nslookup web-server`."], 35),
        _obj("Reverse-lookup the DB Server IP",
             "Given 192.168.1.30, find out which host owns it.",
             "event_emitted", {"event": "nslookup", "key": "target", "equals": "db-server"},
             ["nslookup works with IP addresses too.",
              "Try `nslookup 192.168.1.30`.",
              "The response shows `name = db-server`."], 35),
        _obj("Experience an NXDOMAIN",
             "Try to resolve a hostname that doesn't exist on the network.",
             "event_emitted", {"event": "nslookup", "key": "resolved", "equals": False},
             ["Any name that isn't a real device will fail.",
              "Try `nslookup fake-server`.",
              "You should see `NXDOMAIN` — the DNS equivalent of 'not found'."], 40),
        _obj("Identify the DNS server in use",
             "Run nslookup and note the Server line at the top of the output.",
             "state_flag", {"path": "flags.nslookup_hosts", "min_length": 2},
             ["Every nslookup output begins with the DNS server address.",
              "Run nslookup on two different hostnames.",
              "The Server line shows the DNS resolver this device is configured to use."], 50),
    ]),

    # ------------------------------------------------------------------
    # Lab 5: Service Discovery (YC-026.5)
    # ------------------------------------------------------------------
    ("net-services", "Service Discovery", "Medium", 20, 200, [
        _obj("List services on the Web Server",
             "Switch to the Web Server and run netstat to see listening ports.",
             "event_emitted", {"event": "netstat", "key": "host", "equals": "web-server"},
             ["Click Web Server on the topology map first.",
              "Then run `netstat` to see what's listening.",
              "You should see HTTP (80) and HTTPS (443)."], 40),
        _obj("List services on the DB Server",
             "Switch to the DB Server and discover its listening port.",
             "event_emitted", {"event": "netstat", "key": "host", "equals": "db-server"},
             ["Click DB Server on the map, then run `netstat`.",
              "Database servers typically listen on a well-known port.",
              "MySQL listens on port 3306."], 40),
        _obj("Check the Router's open ports",
             "Routers often run SSH and admin interfaces. Verify.",
             "event_emitted", {"event": "netstat", "key": "host", "equals": "router"},
             ["Click the Router on the map.",
              "Run `netstat` on the Router.",
              "Look for SSH (22) and HTTP admin (80)."], 40),
        _obj("Generate an ESTABLISHED connection",
             "Ping the Web Server from PC-1, then check netstat on the Web Server.",
             "state_flag", {"path": "flags.pinged", "min_length": 3},
             ["First select PC-1 and ping web-server.",
              "Then switch to web-server and run netstat.",
              "You should see an ESTABLISHED connection from PC-1's IP.",
              ], 40),
        _obj("Explore 5 unique hosts",
             "Visit at least 5 different devices during this lab.",
             "state_flag", {"path": "flags.visited", "min_length": 5},
             ["Click each device on the topology map.",
              "Each unique device you select counts toward this objective.",
              "Router + Switch + PC-1 + Web Server + DB Server = 5."], 40),
    ]),

    # ------------------------------------------------------------------
    # Lab 6: Network Troubleshooting (YC-026.5)
    # ------------------------------------------------------------------
    ("net-troubleshoot", "Network Troubleshooting", "Medium", 25, 240, [
        _obj("Verify PC-1's network configuration",
             "Run ifconfig on PC-1 and confirm it has a valid IP and gateway.",
             "event_emitted", {"event": "ipconfig", "key": "host", "equals": "pc-1"},
             ["Select PC-1 and run `ifconfig` (or `ipconfig`).",
              "Check the IP address, subnet mask, and default gateway.",
              "PC-1 should be on 192.168.1.10 with gateway 192.168.1.1."], 35),
        _obj("Verify PC-2's Windows configuration",
             "Run ipconfig on the Windows PC and note the difference in format.",
             "event_emitted", {"event": "ipconfig", "key": "host", "equals": "pc-2"},
             ["Select PC-2 (Windows 11) and run `ipconfig`.",
              "Notice the Windows-style output vs Linux ifconfig.",
              "Check Subnet Mask, Default Gateway, and Physical Address."], 35),
        _obj("Test gateway reachability",
             "Ping the default gateway from PC-1 to confirm basic connectivity.",
             "event_emitted", {"event": "ping", "key": "target", "equals": "192.168.1.1"},
             ["The default gateway is the Router at 192.168.1.1.",
              "Select PC-1 and run `ping 192.168.1.1`.",
              "A successful ping means the gateway is reachable."], 40),
        _obj("Trace the full path to the DB Server",
             "Use traceroute to see every hop from PC-1 to the DB Server.",
             "event_emitted", {"event": "traceroute", "key": "target", "equals": "db-server"},
             ["Select PC-1 and run `traceroute db-server`.",
              "Each hop shows the intermediate device and its latency.",
              "The path goes through the core switch."], 40),
        _obj("Check the routing table",
             "View PC-1's routing table to understand how traffic is forwarded.",
             "event_emitted", {"event": "route", "key": "host", "equals": "pc-1"},
             ["Select PC-1 and run `route`.",
              "The `default` row points at the gateway.",
              "The subnet row shows the local 192.168.1.0/24 network."], 40),
        _obj("Verify DNS resolution works end-to-end",
             "Resolve the Web Server's hostname, then ping the IP you got back.",
             "state_flag", {"path": "flags.nslookup_hosts", "min_length": 1},
             ["Run `nslookup web-server` to get its IP.",
              "Then `ping 192.168.1.20` to verify connectivity.",
              "This is the standard troubleshooting workflow: resolve → ping."], 50),
    ]),
]


# ("Interactive Explorer" attaches to the existing per-category
# networking_labs_completed metric established in YC-013.0.)
ACHIEVEMENTS = [
    ("Interactive Explorer",
     "Complete the interactive network simulator's first lab.",
     "share-2", "labs", "networking_labs_completed", 4, 150),
    # YC-026.5 — new milestones for the extended lab set.
    ("Network Analyst",
     "Complete all 6 interactive networking labs.",
     "share-2", "labs", "networking_labs_completed", 9, 300),
    ("Service Hunter",
     "Discover listening services across multiple hosts.",
     "cpu", "labs", "networking_labs_completed", 7, 200),
]


def seed_interactive_network() -> dict[str, int]:
    """Seed the 3 interactive-network labs + the achievement. Idempotent."""
    # Register the simulator engine key (used by the registry & routes).
    if SimulatorEngine.query.filter_by(key="net-interactive").first() is None:
        db.session.add(SimulatorEngine(
            key="net-interactive",
            name="Interactive Network",
            description="Multi-device virtual network with clickable topology.",
        ))
        db.session.flush()

    category = LabCategory.query.filter_by(slug="networking").first()
    if category is None:
        category = LabCategory(
            slug="networking", name="Networking", icon="share-2",
            color="teal",
            description="Learn networking hands-on with an interactive lab environment.",
            display_order=20, is_active=True,
        )
        db.session.add(category)
        db.session.flush()

    created = {"labs": 0, "objectives": 0, "achievements": 0}

    # Continue the display order after any previously-seeded networking labs.
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
            description=f"{title} — interactive multi-device network lab.",
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

    # Achievement (idempotent per title).
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
