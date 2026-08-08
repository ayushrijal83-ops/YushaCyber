"""Tests for YC-034.8 — Network Reconnaissance interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0348-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_recon.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.network import build_network
from app.core.terminal.shell import Shell

_CONFIG = {
    "student_ip": "10.0.0.5",
    "hosts": {
        "10.0.0.5": {"hostname": "student-pc",
                    "interfaces": [{"name": "eth0", "ip": "10.0.0.5", "cidr": 24, "state": "UP"}]},
        "10.0.0.1": {"hostname": "gateway", "reachable": True},
        "10.0.0.10": {"hostname": "web", "reachable": True,
                     "services": [{"port": 80, "proto": "tcp", "name": "http"}]},
        "10.0.0.40": {"hostname": "blocked", "reachable": True, "blocks_icmp": True,
                     "services": [{"port": 22, "proto": "tcp", "name": "ssh"}]},
        "10.0.1.99": {"hostname": "other-subnet", "reachable": True},
    },
}

SOLVE: list[str] = [
    "nmap -sn 10.10.10.0/24",
    "nmap 10.10.10.40",
    "nmap -p- 10.10.10.40",
    "nmap -sV 10.10.10.40",
    "nmap -sV 10.10.10.30",
    ('echo "Host: 10.10.10.40 (training-server) - Ports: 22,3306,8080 - Services: '
     'SSH,MySQL,HTTP" > recon/findings.txt'),
    'echo "TARGET: 10.10.10.40" >> recon/findings.txt',
    'echo "Services: SSH,MySQL,HTTP" >> recon/findings.txt',
    ('echo "PRIMARY TARGET CONFIRMED: 10.10.10.40 exposes SSH, MySQL, and HTTP - '
     'highest service diversity" >> recon/findings.txt'),
]


# ═══════════════════════════════════════════
# Host discovery (-sn / CIDR) — framework level
# ═══════════════════════════════════════════
class TestHostDiscovery:
    def test_discovers_hosts_in_range(self):
        net = build_network(_CONFIG)
        results = {r["ip"]: r["up"] for r in net.discover("10.0.0.0/24")}
        assert results["10.0.0.1"] is True
        assert results["10.0.0.10"] is True

    def test_excludes_hosts_outside_range(self):
        net = build_network(_CONFIG)
        results = {r["ip"] for r in net.discover("10.0.0.0/24")}
        assert "10.0.1.99" not in results

    def test_icmp_blocking_host_reports_down_in_sweep(self):
        net = build_network(_CONFIG)
        results = {r["ip"]: r["up"] for r in net.discover("10.0.0.0/24")}
        assert results["10.0.0.40"] is False

    def test_invalid_cidr_returns_empty(self):
        net = build_network(_CONFIG)
        assert net.discover("not-a-cidr") == []

    def test_format_discovery_lists_only_up_hosts(self):
        net = build_network(_CONFIG)
        results = net.discover("10.0.0.0/24")
        out = net.format_discovery("10.0.0.0/24", results)
        assert "10.0.0.1" in out
        assert "10.0.0.40" not in out  # blocked host omitted, not listed as down
        assert "hosts up" in out

    def test_real_world_cidr_finds_nothing(self):
        # 8.8.8.0/24 isn't in the simulated topology at all.
        net = build_network(_CONFIG)
        results = net.discover("8.8.8.0/24")
        assert results == []


class TestDiscoveryCommand:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.network = build_network(_CONFIG)
        return sh

    def test_sn_flag_triggers_discovery(self):
        sh = self._shell()
        out = sh.execute("nmap -sn 10.0.0.0/24")
        assert "Host is up" in out
        assert "10.0.0.1" in out

    def test_sn_without_target(self):
        sh = self._shell()
        out = sh.execute("nmap -sn")
        assert "no target specified" in out

    def test_sn_does_not_affect_normal_scan(self):
        sh = self._shell()
        out = sh.execute("nmap 10.0.0.10")
        assert "80/tcp open http" in out


# ═══════════════════════════════════════════
# Validator — list-of-alternatives (generic, reusable)
# ═══════════════════════════════════════════
class TestAlternativesMatch:
    def test_command_accepts_any_listed_alternative(self):
        sh = Shell()
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "command", "match": ["nmap 10.10.10.10", "nmap 10.10.10.30"]}}
        assert validate(obj, sh, command="nmap 10.10.10.30").passed
        assert validate(obj, sh, command="nmap 10.10.10.10").passed
        assert not validate(obj, sh, command="nmap 10.10.10.99").passed

    def test_output_contains_accepts_any_listed_alternative(self):
        sh = Shell()
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "output_contains", "match": ["foo", "bar"]}}
        assert validate(obj, sh, output="contains bar here").passed
        assert not validate(obj, sh, output="contains baz here").passed

    def test_file_contains_accepts_any_listed_alternative(self):
        sh = Shell()
        sh.fs.write("notes.txt", "alpha content")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "file_contains", "match": ["alpha", "beta"], "path": "notes.txt"}}
        assert validate(obj, sh).passed

    def test_plain_string_match_still_works(self):
        # Backward compatibility — every pre-existing mission passes a
        # plain string, never a list.
        sh = Shell()
        obj = {"id": "x", "xp": 10, "validate": {"type": "command", "match": "pwd"}}
        assert validate(obj, sh, command="pwd").passed
        assert not validate(obj, sh, command="ls").passed


# ═══════════════════════════════════════════
# AI context additions (generic, reusable)
# ═══════════════════════════════════════════
class TestAiContextAdditions:
    def test_last_output_tracked(self):
        r = MissionRunner("network-reconnaissance", 1)
        r.execute("nmap -sn 10.10.10.0/24")
        ctx = r.ai_context()
        assert "Nmap done" in ctx["last_output"]

    def test_scanned_targets_derived_from_history(self):
        r = MissionRunner("network-reconnaissance", 2)
        r.execute("nmap 10.10.10.40")
        r.execute("nmap -sV 10.10.10.30")
        ctx = r.ai_context()
        assert "10.10.10.40" in ctx["scanned_targets"]
        assert "10.10.10.30" in ctx["scanned_targets"]

    def test_non_nmap_commands_excluded_from_scanned_targets(self):
        r = MissionRunner("network-reconnaissance", 3)
        r.execute("cat /etc/hosts")  # mentions IPs but isn't an nmap command
        ctx = r.ai_context()
        assert ctx["scanned_targets"] == []


# ═══════════════════════════════════════════
# Security isolation — structural, not just behavioral
# ═══════════════════════════════════════════
class TestSecurityIsolation:
    def test_network_module_has_no_network_capable_imports(self):
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
        assert "ipaddress" in imported  # present, but it's pure CIDR arithmetic

    def test_nmap_handler_body_has_no_shell_execution(self):
        import inspect

        from app.core.terminal import commands as cmdmod
        src = inspect.getsource(cmdmod._nmap)
        body = src.split('"""', 2)[-1]
        for forbidden in ("subprocess.", "os.system(", "os.popen(", "shell=True",
                          "Popen(", "eval(", "exec("):
            assert forbidden not in body

    def test_discover_never_touches_real_addresses(self):
        net = build_network(_CONFIG)
        for cidr in ("8.8.8.0/24", "1.1.1.0/24", "127.0.0.0/24"):
            assert net.discover(cidr) == []

    def test_scan_of_real_world_ip_is_pure_lookup(self):
        net = build_network(_CONFIG)
        for ip in ("8.8.8.8", "1.1.1.1", "127.0.0.1"):
            r = net.scan(ip)
            assert not r.host_up
            assert r.ports == []


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "network-reconnaissance" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("network-reconnaissance")
        assert m is not None
        assert m["title"] == "Network Reconnaissance"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 450

    def test_objective_count(self):
        m = get_mission("network-reconnaissance")
        assert len(m["objectives"]) == 11

    def test_xp_sums_to_total(self):
        m = get_mission("network-reconnaissance")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_chained_after_nmap_fundamentals(self):
        assert MISSIONS["nmap-fundamentals"]["next_mission"] == "network-reconnaissance"

    def test_authorized_engagement_framing(self):
        m = get_mission("network-reconnaissance")
        assert "authorized" in m["description"].lower()
        assert "simulated" in m["description"].lower()

    def test_recon_workspace_seeded(self):
        m = get_mission("network-reconnaissance")
        assert "recon" in m["filesystem"]["home"]["student"]

    def test_training_server_has_most_diverse_services(self):
        m = get_mission("network-reconnaissance")
        services = m["network"]["hosts"]["10.10.10.40"]["services"]
        names = {s["name"] for s in services}
        assert names == {"ssh", "mysql", "http"}


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("network-reconnaissance", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 450
        assert set(r.progress.completed_ids) == {f"rn-{i}" for i in range(1, 12)}

    def test_investigate_objective_accepts_any_real_server(self):
        r = MissionRunner("network-reconnaissance", 2)
        r.execute("nmap -sn 10.10.10.0/24")
        r.execute("nmap 10.10.10.10")  # web-server, not training-server
        assert "rn-2" in r.progress.completed_ids

    def test_compare_objective_accepts_either_alternate_host(self):
        r = MissionRunner("network-reconnaissance", 3)
        r.execute("nmap -sV 10.10.10.30")  # file-server, the other alternate
        assert "rn-6" in r.progress.completed_ids

    def test_capstone_requires_actually_writing_confirmation(self):
        r = MissionRunner("network-reconnaissance", 4)
        r.execute("nmap -sn 10.10.10.0/24")
        r.execute("nmap -sV 10.10.10.40")
        r.execute('echo "Host: 10.10.10.40" > recon/findings.txt')
        assert "rn-11" not in r.progress.completed_ids
        r.execute('echo "TARGET: 10.10.10.40" >> recon/findings.txt')
        assert "rn-11" not in r.progress.completed_ids
        r.execute('echo "PRIMARY TARGET CONFIRMED: it is 10.10.10.40" >> recon/findings.txt')
        assert "rn-11" in r.progress.completed_ids

    def test_progress_partial(self):
        r = MissionRunner("network-reconnaissance", 5)
        r.execute("nmap -sn 10.10.10.0/24")
        assert len(r.progress.completed_ids) == 1
        assert not r.progress.completed

    def test_hint(self):
        r = MissionRunner("network-reconnaissance", 6)
        hint = r.use_hint("rn-1")
        assert "-sn" in hint
        assert r.progress.hints_used == 1

    def test_ai_context(self):
        r = MissionRunner("network-reconnaissance", 7)
        ctx = r.ai_context()
        assert ctx["mission"] == "Network Reconnaissance"
        assert ctx["current_objective"] == "Discover Hosts"

    def test_save_restore(self):
        r = MissionRunner("network-reconnaissance", 8)
        r.execute("nmap -sn 10.10.10.0/24")
        r.execute('echo "notes" > recon/findings.txt')
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        assert "rn-1" in r2.progress.completed_ids
        assert r2.shell.fs.read("recon/findings.txt") == "notes\n"
        out = r2.shell.execute("nmap -sV 10.10.10.40")
        assert "MySQL 8.x" in out


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
        u = User(username="recon_test", email="recontest@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "recon_test", uid


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

            assert mission_status(uid, "network-reconnaissance") == "locked"

            for slug, commands in _PREREQ_MISSIONS:
                start_mission(uid, slug)
                for c in commands:
                    execute_command(uid, slug, c)

            assert mission_status(uid, "network-reconnaissance") == "available"

            start_mission(uid, "network-reconnaissance")
            for c in SOLVE:
                execute_command(uid, "network-reconnaissance", c)

            assert mission_status(uid, "network-reconnaissance") == "completed"

            user = User.query.get(uid)
            # 200+200+250+300+350+400+450 = 2150 base, plus no-hints bonuses.
            assert user.xp > 2150
            assert user.level > 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] == 7
            assert stats["xp_earned"] > 2150


# ═══════════════════════════════════════════
# HTTP — discovery/detail pick up the new mission automatically
# ═══════════════════════════════════════════
class TestHTTP:
    def test_discover_page_lists_network_reconnaissance(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
            assert b"Network Reconnaissance" in r.data

    def test_detail_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/network-reconnaissance")
            assert r.status_code == 200
            assert b"Attack-surface comparison" in r.data

    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "network-reconnaissance" in ids
