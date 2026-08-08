"""Tests for YC-034.7 — Nmap Fundamentals interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0347-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_nmap.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.terminal.network import build_network
from app.core.terminal.shell import Shell

_CONFIG = {
    "student_ip": "10.0.0.5",
    "hosts": {
        "10.0.0.5": {"hostname": "student-pc",
                    "interfaces": [{"name": "eth0", "ip": "10.0.0.5", "cidr": 24, "state": "UP"}]},
        "10.0.0.10": {
            "hostname": "web01", "reachable": True,
            "services": [
                {"port": 22, "proto": "tcp", "name": "ssh", "version": "OpenSSH 9.x"},
                {"port": 80, "proto": "tcp", "name": "http", "version": "nginx"},
                {"port": 443, "proto": "tcp", "name": "https", "version": "nginx"},
            ],
            "filtered_ports": [25],
        },
        "10.0.0.53": {
            "hostname": "dns01", "reachable": True,
            "services": [{"port": 53, "proto": "udp", "name": "dns", "version": "BIND 9.x"}],
        },
        "10.0.0.40": {
            "hostname": "training", "reachable": True, "blocks_icmp": True,
            "os_guess": "Linux 5.X (embedded)",
            "services": [{"port": 22, "proto": "tcp", "name": "ssh", "version": "OpenSSH 8.x"}],
        },
    },
}

SOLVE: list[str] = [
    "nmap 10.10.10.10",
    "nmap -p 22,80,443 10.10.10.10",
    "nmap -sV 10.10.10.10",
    "nmap -sT 10.10.10.10",
    "nmap -sU 10.10.10.53",
    "nmap 10.10.10.40",
    "nmap -Pn -O 10.10.10.40",
    "nmap -sV 10.10.10.30",
]


# ═══════════════════════════════════════════
# Scan engine — framework level (mission-agnostic)
# ═══════════════════════════════════════════
class TestScanEngine:
    def test_default_scan_returns_known_ports(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.10")
        ports = {e["port"]: e["state"] for e in r.ports}
        assert ports[22] == "open"
        assert ports[80] == "open"
        assert ports[25] == "filtered"

    def test_targeted_port_scan(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.10", ports=[22, 80, 443])
        assert [e["port"] for e in r.ports] == [22, 80, 443]

    def test_closed_port_when_explicitly_requested(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.10", ports=[9999])
        assert r.ports[0]["state"] == "closed"
        assert r.ports[0]["service"] == "unknown"

    def test_service_detection_includes_version(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.10", service_detection=True)
        ssh = next(e for e in r.ports if e["port"] == 22)
        assert ssh["version"] == "OpenSSH 9.x"

    def test_no_service_detection_omits_version(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.10", service_detection=False)
        ssh = next(e for e in r.ports if e["port"] == 22)
        assert ssh["version"] is None

    def test_udp_scan(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.53", proto="udp")
        assert r.ports[0]["proto"] == "udp"
        assert r.ports[0]["state"] == "open"
        assert r.ports[0]["service"] == "dns"

    def test_unknown_target_is_down(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.99")
        assert not r.host_up
        assert r.ports == []

    def test_icmp_blocking_host_appears_down_by_default(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.40")
        assert not r.host_up

    def test_skip_discovery_bypasses_icmp_block(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.40", skip_discovery=True)
        assert r.host_up
        assert r.os_guess == "Linux 5.X (embedded)"

    def test_format_nmap_open_ports(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.10")
        out = net.format_nmap(r)
        assert "Starting Nmap" in out
        assert "Nmap scan report for 10.0.0.10" in out
        assert "22/tcp open ssh" in out
        assert "Nmap done." in out

    def test_format_nmap_down_host_mentions_pn(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.40")
        out = net.format_nmap(r)
        assert "-Pn" in out

    def test_format_nmap_with_os(self):
        net = build_network(_CONFIG)
        r = net.scan("10.0.0.40", skip_discovery=True)
        out = net.format_nmap(r, show_os=True)
        assert "Linux 5.X" in out


# ═══════════════════════════════════════════
# nmap command — flag parsing
# ═══════════════════════════════════════════
class TestNmapCommand:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.network = build_network(_CONFIG)
        return sh

    def test_no_network_configured(self):
        sh = Shell()
        assert sh.execute("nmap 10.0.0.10") == "nmap: no network configured for this session"

    def test_no_args(self):
        sh = self._shell()
        assert "Usage: nmap" in sh.execute("nmap")

    def test_flags_without_target(self):
        sh = self._shell()
        assert "no target specified" in sh.execute("nmap -sV")

    def test_basic_scan(self):
        sh = self._shell()
        out = sh.execute("nmap 10.0.0.10")
        assert "22/tcp open ssh" in out

    def test_port_flag(self):
        sh = self._shell()
        out = sh.execute("nmap -p 22,443 10.0.0.10")
        assert "22/tcp open ssh" in out
        assert "80/tcp" not in out
        assert "443/tcp open https" in out

    def test_port_flag_range(self):
        sh = self._shell()
        out = sh.execute("nmap -p 20-25 10.0.0.10")
        assert "22/tcp open ssh" in out
        assert "25/tcp filtered" in out

    def test_all_ports_flag(self):
        sh = self._shell()
        out = sh.execute("nmap -p- 10.0.0.10")
        assert "22/tcp open ssh" in out
        assert "25/tcp filtered" in out

    def test_service_version_flag(self):
        sh = self._shell()
        out = sh.execute("nmap -sV 10.0.0.10")
        assert "VERSION" in out
        assert "OpenSSH 9.x" in out

    def test_tcp_connect_flag(self):
        sh = self._shell()
        out = sh.execute("nmap -sT 10.0.0.10")
        assert "22/tcp open ssh" in out

    def test_udp_flag(self):
        sh = self._shell()
        out = sh.execute("nmap -sU 10.0.0.53")
        assert "53/udp open dns" in out

    def test_os_detection_flag(self):
        sh = self._shell()
        out = sh.execute("nmap -Pn -O 10.0.0.40")
        assert "OS guess: Linux 5.X" in out

    def test_pn_flag_bypasses_icmp_block(self):
        sh = self._shell()
        blocked = sh.execute("nmap 10.0.0.40")
        assert "Note: Host seems down" in blocked
        unblocked = sh.execute("nmap -Pn 10.0.0.40")
        assert "22/tcp open ssh" in unblocked

    def test_unrecognized_flag_does_not_crash(self):
        sh = self._shell()
        out = sh.execute("nmap -A 10.0.0.10")
        assert "22/tcp open ssh" in out

    def test_unknown_target(self):
        sh = self._shell()
        out = sh.execute("nmap 10.0.0.250")
        assert "Note: Host seems down" in out


# ═══════════════════════════════════════════
# Security — the simulator must be structurally incapable of touching
# a real network. Static analysis, not just behavioral spot checks.
# ═══════════════════════════════════════════
class TestSecurityIsolation:
    def test_network_module_imports_nothing_network_capable(self):
        import ast

        import app.core.terminal.network as netmod
        with open(netmod.__file__, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"socket", "subprocess", "requests", "urllib", "http", "os", "shutil"}
        assert not (imported & forbidden), f"forbidden imports: {imported & forbidden}"

    def test_commands_module_nmap_handler_has_no_shell_execution(self):
        # Check actual usage, not prose — the handler's own docstring
        # legitimately mentions "subprocess" while explaining it avoids one.
        import inspect

        from app.core.terminal import commands as cmdmod
        src = inspect.getsource(cmdmod._nmap)
        body = src.split('"""', 2)[-1]  # drop the leading docstring
        for forbidden in ("subprocess.", "os.system(", "os.popen(", "shell=True",
                          "Popen(", "eval(", "exec("):
            assert forbidden not in body

    def test_scanning_real_world_addresses_is_pure_lookup(self):
        # 8.8.8.8 / 1.1.1.1 are not in the simulated topology, so they must
        # resolve to "host down" via a plain dict lookup — never an attempt
        # to actually reach them.
        net = build_network(_CONFIG)
        for real_ip in ("8.8.8.8", "1.1.1.1", "127.0.0.1"):
            r = net.scan(real_ip)
            assert not r.host_up
            assert r.ports == []

    def test_nmap_command_module_has_no_network_imports_at_module_level(self):
        import app.core.terminal.commands as cmdmod
        assert not hasattr(cmdmod, "socket")
        assert not hasattr(cmdmod, "subprocess")


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "nmap-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("nmap-fundamentals")
        assert m is not None
        assert m["title"] == "Nmap Fundamentals"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 400

    def test_objective_count(self):
        m = get_mission("nmap-fundamentals")
        assert len(m["objectives"]) == 10

    def test_xp_sums_to_total(self):
        m = get_mission("nmap-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_chained_after_network_troubleshooting(self):
        assert MISSIONS["network-troubleshooting"]["next_mission"] == "nmap-fundamentals"

    def test_responsible_recon_intro(self):
        m = get_mission("nmap-fundamentals")
        assert "permission" in m["description"].lower()
        assert "simulated" in m["description"].lower()

    def test_topology_has_filtered_and_icmp_blocking_hosts(self):
        m = get_mission("nmap-fundamentals")
        fileserver = m["network"]["hosts"]["10.10.10.30"]
        training = m["network"]["hosts"]["10.10.10.40"]
        assert 25 in fileserver["filtered_ports"]
        assert training["blocks_icmp"] is True


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("nmap-fundamentals", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 400
        assert set(r.progress.completed_ids) == {f"nm-{i}" for i in range(1, 11)}

    def test_capstone_not_completed_by_web_server_scans_alone(self):
        r = MissionRunner("nmap-fundamentals", 2)
        for c in SOLVE[:5]:
            r.execute(c)
        assert "nm-10" not in r.progress.completed_ids

    def test_os_detection_objective_requires_pn(self):
        r = MissionRunner("nmap-fundamentals", 3)
        r.execute("nmap -O 10.10.10.40")  # blocked, no -Pn
        assert "nm-9" not in r.progress.completed_ids
        r.execute("nmap -Pn -O 10.10.10.40")
        assert "nm-9" in r.progress.completed_ids

    def test_progress_partial(self):
        r = MissionRunner("nmap-fundamentals", 4)
        r.execute("nmap 10.10.10.10")
        assert len(r.progress.completed_ids) == 3  # nm-1, nm-2, nm-3
        assert not r.progress.completed

    def test_hint(self):
        r = MissionRunner("nmap-fundamentals", 5)
        hint = r.use_hint("nm-5")
        assert "-sV" in hint
        assert r.progress.hints_used == 1

    def test_ai_context(self):
        r = MissionRunner("nmap-fundamentals", 6)
        ctx = r.ai_context()
        assert ctx["mission"] == "Nmap Fundamentals"
        assert ctx["current_objective"] == "Perform a Basic Scan"
        r.execute("nmap 10.10.10.10")
        ctx2 = r.ai_context()
        assert ctx2["last_command"] == "nmap 10.10.10.10"
        assert ctx2["progress_pct"] > 0

    def test_save_restore(self):
        r = MissionRunner("nmap-fundamentals", 7)
        r.execute("nmap 10.10.10.10")
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        assert "nm-1" in r2.progress.completed_ids
        out = r2.shell.execute("nmap -sV 10.10.10.30")
        assert "vsftpd" in out


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
        u = User(username="nmap_test", email="nmaptest@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "nmap_test", uid


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

            assert mission_status(uid, "nmap-fundamentals") == "locked"

            for slug, commands in _PREREQ_MISSIONS:
                start_mission(uid, slug)
                for c in commands:
                    execute_command(uid, slug, c)

            assert mission_status(uid, "nmap-fundamentals") == "available"

            start_mission(uid, "nmap-fundamentals")
            for c in SOLVE:
                execute_command(uid, "nmap-fundamentals", c)

            assert mission_status(uid, "nmap-fundamentals") == "completed"

            user = User.query.get(uid)
            # 200+200+250+300+350+400 = 1700 base, plus no-hints bonuses.
            assert user.xp > 1700
            assert user.level > 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] == 6
            assert stats["xp_earned"] > 1700


# ═══════════════════════════════════════════
# HTTP — discovery/detail pick up the new mission automatically
# ═══════════════════════════════════════════
class TestHTTP:
    def test_discover_page_lists_nmap_fundamentals(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
            assert b"Nmap Fundamentals" in r.data

    def test_detail_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/nmap-fundamentals")
            assert r.status_code == 200
            assert b"Version detection" in r.data

    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "nmap-fundamentals" in ids
