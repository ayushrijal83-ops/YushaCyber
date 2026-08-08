"""Tests for YC-034.9 — Wireshark Fundamentals interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0349-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_wireshark.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.terminal.packets import CAPTURE_REGISTRY, build_packet_lab
from app.core.terminal.shell import Shell

SOLVE: list[str] = [
    "capture handshake", "show 1", "filter tcp", "follow 1",
    "capture mixed", "filter dns",
    "capture http", "filter http", "follow 1",
    "filter ip.addr == 10.10.10.10", "filter tcp.port == 80",
    "capture mixed", "packets",
    "capture investigation", "filter ip.addr == 10.10.10.77",
    ('echo "Source: 10.10.10.20, Destination: 10.10.10.77, Port: 4444, Protocol: TCP, '
     'Reason: uncommon destination and port not part of normal training traffic" '
     '> wireshark/investigation.txt'),
]


# ═══════════════════════════════════════════
# Packet model / captures — framework level
# ═══════════════════════════════════════════
class TestPacketModel:
    def test_all_captures_build(self):
        lab = build_packet_lab(list(CAPTURE_REGISTRY.keys()))
        assert set(lab.captures.keys()) == set(CAPTURE_REGISTRY.keys())

    def test_handshake_capture_structure(self):
        lab = build_packet_lab(["handshake"])
        cap = lab.captures["handshake"]
        assert len(cap.packets) == 3
        assert cap.packets[0].tcp_flags == "SYN"
        assert cap.packets[1].tcp_flags == "SYN, ACK"
        assert cap.packets[2].tcp_flags == "ACK"

    def test_dns_capture_has_query_and_response(self):
        cap = build_packet_lab(["dns"]).captures["dns"]
        assert len(cap.packets) == 2
        assert cap.packets[0].protocol == "DNS"
        assert "example.training" in cap.packets[0].payload_summary
        assert "10.10.10.10" in cap.packets[1].payload_summary

    def test_http_capture_has_get_and_200(self):
        cap = build_packet_lab(["http"]).captures["http"]
        get_pkt = next(p for p in cap.packets if "GET" in p.payload_summary)
        resp_pkt = next(p for p in cap.packets if "200 OK" in p.payload_summary)
        assert get_pkt.application_protocol == "HTTP"
        assert resp_pkt.application_protocol == "HTTP"

    def test_icmp_capture_has_request_and_reply(self):
        cap = build_packet_lab(["icmp"]).captures["icmp"]
        assert len(cap.packets) == 2
        assert "request" in cap.packets[0].payload_summary.lower()
        assert "reply" in cap.packets[1].payload_summary.lower()

    def test_udp_packet_in_mixed(self):
        cap = build_packet_lab(["mixed"]).captures["mixed"]
        udp_packets = [p for p in cap.packets if p.protocol == "UDP"]
        assert len(udp_packets) == 5

    def test_investigation_contains_anomaly(self):
        cap = build_packet_lab(["investigation"]).captures["investigation"]
        suspicious = [p for p in cap.packets if p.dst_ip == "10.10.10.77" or p.src_ip == "10.10.10.77"]
        assert len(suspicious) == 4
        assert any(p.dst_port == 4444 or p.src_port == 4444 for p in suspicious)

    def test_capture_sizes_within_guidance(self):
        # Focused teaching captures stay small; mixed/investigation are
        # deliberately larger so filtering is actually necessary.
        lab = build_packet_lab(list(CAPTURE_REGISTRY.keys()))
        assert len(lab.captures["handshake"].packets) < 10
        assert len(lab.captures["mixed"].packets) >= 20
        assert len(lab.captures["investigation"].packets) >= 20

    def test_conversation_id_is_direction_independent(self):
        cap = build_packet_lab(["handshake"]).captures["handshake"]
        syn = cap.get(1)
        synack = cap.get(2)
        assert syn.conversation_id == synack.conversation_id

    def test_conversation_returns_all_matching_packets(self):
        cap = build_packet_lab(["handshake"]).captures["handshake"]
        conv = cap.get(1).conversation_id
        assert len(cap.conversation(conv)) == 3


# ═══════════════════════════════════════════
# Filtering
# ═══════════════════════════════════════════
class TestFiltering:
    def _mixed(self):
        return build_packet_lab(["mixed"]).captures["mixed"]

    def test_filter_bare_protocol(self):
        cap = self._mixed()
        results = cap.filter("dns")
        assert results
        assert all(p.protocol == "DNS" for p in results)

    def test_filter_tcp_port(self):
        cap = self._mixed()
        results = cap.filter("tcp.port == 80")
        assert results
        assert all(80 in (p.src_port, p.dst_port) for p in results)

    def test_filter_udp_port(self):
        cap = self._mixed()
        results = cap.filter("udp.port == 123")
        assert results
        assert all(p.protocol == "UDP" for p in results)

    def test_filter_ip_addr(self):
        cap = self._mixed()
        results = cap.filter("ip.addr == 10.10.10.53")
        assert results
        assert all("10.10.10.53" in (p.src_ip, p.dst_ip) for p in results)

    def test_filter_ip_src(self):
        cap = self._mixed()
        results = cap.filter("ip.src == 10.10.10.20")
        assert all(p.src_ip == "10.10.10.20" for p in results)

    def test_filter_ip_dst(self):
        cap = self._mixed()
        results = cap.filter("ip.dst == 10.10.10.53")
        assert all(p.dst_ip == "10.10.10.53" for p in results)

    def test_filter_no_match(self):
        cap = self._mixed()
        assert cap.filter("ip.addr == 9.9.9.9") == []

    def test_filter_unknown_expression(self):
        cap = self._mixed()
        assert cap.filter("bogus") == []

    def test_filter_investigation_isolates_anomaly(self):
        cap = build_packet_lab(["investigation"]).captures["investigation"]
        results = cap.filter("ip.addr == 10.10.10.77")
        assert len(results) == 4


# ═══════════════════════════════════════════
# Terminal commands
# ═══════════════════════════════════════════
class TestPacketCommands:
    def _shell(self, captures=None) -> Shell:
        sh = Shell()
        sh.packet_lab = build_packet_lab(captures or list(CAPTURE_REGISTRY.keys()))
        return sh

    def test_no_lab_configured(self):
        sh = Shell()
        assert sh.execute("capture handshake") == "capture: no packet lab configured for this session"
        assert "No capture loaded" in sh.execute("packets")

    def test_capture_lists_available(self):
        sh = self._shell()
        out = sh.execute("capture")
        assert "handshake" in out
        assert "Active capture: none" in out

    def test_capture_open(self):
        sh = self._shell()
        out = sh.execute("capture handshake")
        assert "3 packets loaded" in out
        assert sh.packet_lab.active.name == "handshake"

    def test_capture_unknown_name(self):
        sh = self._shell()
        out = sh.execute("capture bogus")
        assert "unknown capture" in out

    def test_packets_without_open_capture(self):
        sh = self._shell()
        assert "No capture loaded" in sh.execute("packets")

    def test_packets_lists_all(self):
        sh = self._shell()
        sh.execute("capture handshake")
        out = sh.execute("packets")
        assert "SYN" in out and "ACK" in out

    def test_show_packet(self):
        sh = self._shell()
        sh.execute("capture handshake")
        out = sh.execute("show 1")
        assert "Packet #1" in out
        assert "Source Port: 49152" in out
        assert sh.packet_lab.selected_packet == 1

    def test_packet_alias(self):
        sh = self._shell()
        sh.execute("capture handshake")
        out = sh.execute("packet 1")
        assert "Packet #1" in out

    def test_show_missing_number(self):
        sh = self._shell()
        sh.execute("capture handshake")
        assert "Usage: show" in sh.execute("show")

    def test_show_unknown_packet(self):
        sh = self._shell()
        sh.execute("capture handshake")
        assert "not found" in sh.execute("show 999")

    def test_follow_by_packet_number(self):
        sh = self._shell()
        sh.execute("capture handshake")
        out = sh.execute("follow 1")
        assert "Conversation:" in out
        assert "SYN, ACK" in out

    def test_follow_no_conversation(self):
        sh = self._shell()
        sh.execute("capture icmp")
        out = sh.execute("follow 999")
        assert "no conversation" in out or "has no conversation" in out

    def test_filter_command(self):
        sh = self._shell()
        sh.execute("capture handshake")
        out = sh.execute("filter tcp")
        assert "SYN" in out
        assert sh.packet_lab.last_filter == "tcp"

    def test_filter_no_matches_message(self):
        sh = self._shell()
        sh.execute("capture handshake")
        out = sh.execute("filter dns")
        assert "No packets matched" in out


# ═══════════════════════════════════════════
# Security isolation — structural, not just behavioral
# ═══════════════════════════════════════════
class TestSecurityIsolation:
    def test_packets_module_has_no_network_capable_imports(self):
        import ast

        import app.core.terminal.packets as pktmod
        with open(pktmod.__file__, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"socket", "subprocess", "requests", "urllib", "http", "os",
                    "shutil", "scapy", "pcap", "pyshark"}
        assert not (imported & forbidden), f"forbidden imports: {imported & forbidden}"

    def test_packet_command_handlers_have_no_shell_execution(self):
        import inspect

        from app.core.terminal import commands as cmdmod
        for fn in (cmdmod._capture, cmdmod._packets, cmdmod._show_packet,
                  cmdmod._follow, cmdmod._filter):
            src = inspect.getsource(fn)
            body = src.split('"""', 2)[-1] if '"""' in src else src
            for forbidden in ("subprocess.", "os.system(", "os.popen(", "shell=True",
                              "Popen(", "eval(", "exec(", "socket."):
                assert forbidden not in body, f"{fn.__name__} contains {forbidden!r}"

    def test_captures_are_deterministic(self):
        lab_a = build_packet_lab(["mixed", "investigation"])
        lab_b = build_packet_lab(["mixed", "investigation"])
        assert lab_a.captures["mixed"].packets == lab_b.captures["mixed"].packets
        assert lab_a.captures["investigation"].packets == lab_b.captures["investigation"].packets

    def test_filters_operate_only_on_simulated_packets(self):
        # A filter can only ever return objects already present in the
        # capture's own in-memory list — never construct or fetch new data.
        cap = build_packet_lab(["mixed"]).captures["mixed"]
        results = cap.filter("tcp")
        assert all(p in cap.packets for p in results)


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "wireshark-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("wireshark-fundamentals")
        assert m is not None
        assert m["title"] == "Wireshark Fundamentals"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 450

    def test_objective_count(self):
        m = get_mission("wireshark-fundamentals")
        assert len(m["objectives"]) == 12

    def test_xp_sums_to_total(self):
        m = get_mission("wireshark-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_chained_after_network_reconnaissance(self):
        assert MISSIONS["network-reconnaissance"]["next_mission"] == "wireshark-fundamentals"

    def test_packet_captures_configured(self):
        m = get_mission("wireshark-fundamentals")
        assert set(m["packet_captures"]) == set(CAPTURE_REGISTRY.keys())

    def test_wireshark_workspace_seeded(self):
        m = get_mission("wireshark-fundamentals")
        assert "wireshark" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("wireshark-fundamentals", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 450
        assert set(r.progress.completed_ids) == {f"wf-{i}" for i in range(1, 13)}

    def test_dns_filter_finds_nothing_in_handshake_capture(self):
        r = MissionRunner("wireshark-fundamentals", 2)
        r.execute("capture handshake")
        r.execute("filter dns")
        assert "wf-6" not in r.progress.completed_ids

    def test_final_investigation_requires_writing_conclusion(self):
        r = MissionRunner("wireshark-fundamentals", 3)
        r.execute("capture investigation")
        r.execute("filter ip.addr == 10.10.10.77")
        assert "wf-12" not in r.progress.completed_ids
        r.execute('echo "Destination: 10.10.10.77" > wireshark/investigation.txt')
        assert "wf-12" in r.progress.completed_ids

    def test_progress_partial(self):
        r = MissionRunner("wireshark-fundamentals", 4)
        r.execute("capture handshake")
        assert len(r.progress.completed_ids) == 1
        assert not r.progress.completed

    def test_hint(self):
        r = MissionRunner("wireshark-fundamentals", 5)
        hint = r.use_hint("wf-4")
        assert "follow" in hint.lower()
        assert r.progress.hints_used == 1

    def test_ai_context_includes_packet_lab(self):
        r = MissionRunner("wireshark-fundamentals", 6)
        r.execute("capture handshake")
        r.execute("show 2")
        r.execute("filter tcp")
        ctx = r.ai_context()
        assert ctx["packet_lab"]["active_capture"] == "handshake"
        assert ctx["packet_lab"]["selected_packet"] == 2
        assert ctx["packet_lab"]["last_filter"] == "tcp"

    def test_save_restore_preserves_packet_lab_state(self):
        r = MissionRunner("wireshark-fundamentals", 7)
        r.execute("capture http")
        r.execute("show 4")
        r.execute("filter http")
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        status = r2.packet_lab_status()
        assert status["active_capture"] == "http"
        assert status["selected_packet"] == 4
        assert status["last_filter"] == "http"
        out = r2.shell.execute("show 4")
        assert "GET /index.html" in out

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("wireshark-fundamentals", 8)
        r1.execute("capture handshake")
        r2 = MissionRunner("wireshark-fundamentals", 9)
        assert r2.packet_lab_status()["active_capture"] is None


# ═══════════════════════════════════════════
# Services — status/chain, persistence, real XP engine
# ═══════════════════════════════════════════
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    a = create_app()
    a.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with a.app_context():
        db.create_all()
    yield a


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        u = User(username="wireshark_test", email="wiresharktest@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "wireshark_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


_PREREQ_MISSIONS: list[tuple[str, list[str]]] = [
    ("linux-basics", ["pwd", "ls", "ls -la", "cd Documents", "cat welcome.txt",
                      "cd ~", "touch notes.txt", "mkdir practice", "history"]),
    ("linux-permissions", ["cd permissions", "ls -l", "whoami", "id", "groups",
                           "cat private.txt", "chmod 644 challenge.txt",
                           "ls -l challenge.txt", "chown student private.txt"]),
    ("bash-fundamentals", ["cd bash-lab", 'name="student"', 'echo "$name"',
                           'export LAB="yushacyber"', 'echo "$LAB"', "current=$(pwd)",
                           "ls | grep txt", "ls > output.txt",
                           '''echo 'echo "Hello from YushaCyber!"' > script.sh''',
                           "chmod +x script.sh", "./script.sh",
                           'if [ -f script.sh ]; then echo "found"; fi',
                           'for i in 1 2 3; do echo "count-$i"; done']),
    ("networking-fundamentals", ["ip addr", "ip route", "ping 10.10.10.1",
                                 "ping 10.10.10.10", "ss", "nslookup example.local",
                                 "cat /etc/hosts", "ping 10.10.10.30"]),
    ("network-troubleshooting", ["ping 10.10.10.1", "ip link", "ip link set eth0 up",
                                 "ip addr", "ip addr add 10.10.10.20/24 dev eth0",
                                 "ip route", "ip route add default via 10.10.10.1",
                                 "ping 10.10.10.1", "ping 10.10.10.10",
                                 "nslookup example.local", "ss"]),
    ("nmap-fundamentals", ["nmap 10.10.10.10", "nmap -p 22,80,443 10.10.10.10",
                           "nmap -sV 10.10.10.10", "nmap -sT 10.10.10.10",
                           "nmap -sU 10.10.10.53", "nmap 10.10.10.40",
                           "nmap -Pn -O 10.10.10.40", "nmap -sV 10.10.10.30"]),
    ("network-reconnaissance", [
        "nmap -sn 10.10.10.0/24", "nmap 10.10.10.40", "nmap -p- 10.10.10.40",
        "nmap -sV 10.10.10.40", "nmap -sV 10.10.10.30",
        ('echo "Host: 10.10.10.40 (training-server) - Ports: 22,3306,8080 - Services: '
         'SSH,MySQL,HTTP" > recon/findings.txt'),
        'echo "TARGET: 10.10.10.40" >> recon/findings.txt',
        'echo "Services: SSH,MySQL,HTTP" >> recon/findings.txt',
        ('echo "PRIMARY TARGET CONFIRMED: 10.10.10.40 exposes SSH, MySQL, and HTTP - '
         'highest service diversity" >> recon/findings.txt'),
    ]),
]


class TestServices:
    def test_full_chain_unlocks_and_completes_with_real_xp(self, app, student):
        _uname, uid = student
        with app.app_context():
            from app.auth.models import User
            from app.core.missions import (
                dashboard_stats,
                execute_command,
                mission_status,
                start_mission,
            )

            assert mission_status(uid, "wireshark-fundamentals") == "locked"

            for slug, commands in _PREREQ_MISSIONS:
                start_mission(uid, slug)
                for c in commands:
                    execute_command(uid, slug, c)

            assert mission_status(uid, "wireshark-fundamentals") == "available"

            start_mission(uid, "wireshark-fundamentals")
            for c in SOLVE:
                execute_command(uid, "wireshark-fundamentals", c)

            assert mission_status(uid, "wireshark-fundamentals") == "completed"

            user = User.query.get(uid)
            # 200+200+250+300+350+400+450+450 = 2600 base, plus no-hints bonuses.
            assert user.xp > 2600
            assert user.level > 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] == 8
            assert stats["xp_earned"] > 2600


# ═══════════════════════════════════════════
# HTTP — discovery/detail/terminal pick up the new mission automatically
# ═══════════════════════════════════════════
class TestHTTP:
    def test_discover_page_lists_wireshark_fundamentals(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
            assert b"Wireshark Fundamentals" in r.data

    def test_detail_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/wireshark-fundamentals")
            assert r.status_code == 200
            assert b"TCP three-way handshake" in r.data

    def test_terminal_page_shows_packet_lab_panel(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/wireshark-fundamentals")
            assert r.status_code == 200
            assert b"data-pkt-status" in r.data

    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "wireshark-fundamentals" in ids
