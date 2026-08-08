"""Tests for YC-034.6 — Network Troubleshooting interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0346-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_troubleshooting.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.network import build_network
from app.core.terminal.shell import Shell

_BROKEN_CONFIG = {
    "student_ip": "10.0.0.5",
    "dns_server_ip": "10.0.0.53",
    "dns_working": False,
    "hosts": {
        "10.0.0.5": {
            "hostname": "test-pc",
            "interfaces": [
                {"name": "eth0", "ip": "10.0.9.9", "cidr": 24, "state": "DOWN"},
                {"name": "lo", "ip": "127.0.0.1", "cidr": 8, "state": "UP"},
            ],
            "routes": [{"destination": "default", "via": "10.0.9.1",
                       "dev": "eth0", "is_default": True}],
            "services": [{"port": 22, "proto": "tcp", "name": "ssh"}],
        },
        "10.0.0.1": {"hostname": "gw", "reachable": True},
    },
    "dns_records": [{"hostname": "svc.local", "ip": "10.0.0.1"}],
}

SOLVE: list[str] = [
    "ping 10.10.10.1",
    "ip link",
    "ip link set eth0 up",
    "ip addr",
    "ip addr add 10.10.10.20/24 dev eth0",
    "ip route",
    "ip route add default via 10.10.10.1",
    "ping 10.10.10.1",
    "ping 10.10.10.10",
    "nslookup example.local",
    "ss",
]


# ═══════════════════════════════════════════
# Network simulator — mutation/persistence primitives (framework level)
# ═══════════════════════════════════════════
class TestNetworkMutations:
    def test_starts_down_with_wrong_ip_and_gateway(self):
        net = build_network(_BROKEN_CONFIG)
        assert net.student.interfaces[0].state == "DOWN"
        assert net.student.interfaces[0].ip == "10.0.9.9"
        assert net.default_gateway() == "10.0.9.1"

    def test_ping_fails_while_interface_down(self):
        net = build_network(_BROKEN_CONFIG)
        ok, out = net.ping("10.0.0.1")
        assert not ok
        assert "Network is unreachable" in out

    def test_set_interface_state_fixes_connectivity_precondition(self):
        net = build_network(_BROKEN_CONFIG)
        assert net.set_interface_state("eth0", "up")
        assert net.student.interfaces[0].state == "UP"
        ok, out = net.ping("10.0.0.1")
        assert ok
        assert "64 bytes from 10.0.0.1" in out

    def test_set_interface_state_unknown_interface(self):
        net = build_network(_BROKEN_CONFIG)
        assert not net.set_interface_state("eth9", "up")

    def test_set_interface_address(self):
        net = build_network(_BROKEN_CONFIG)
        assert net.set_interface_address("eth0", "10.0.0.5", 24)
        assert net.student.interfaces[0].ip == "10.0.0.5"
        assert net.student.interfaces[0].cidr == 24

    def test_set_default_gateway_replaces_existing(self):
        net = build_network(_BROKEN_CONFIG)
        net.set_default_gateway("10.0.0.1")
        assert net.default_gateway() == "10.0.0.1"

    def test_set_default_gateway_adds_when_missing(self):
        net = build_network({**_BROKEN_CONFIG, "hosts": {
            "10.0.0.5": {"hostname": "test-pc",
                        "interfaces": [{"name": "eth0", "ip": "10.0.9.9",
                                       "cidr": 24, "state": "UP"}]},
            "10.0.0.1": {"hostname": "gw", "reachable": True},
        }})
        assert net.default_gateway() is None
        net.set_default_gateway("10.0.0.1")
        assert net.default_gateway() == "10.0.0.1"

    def test_dns_broken_independent_of_connectivity(self):
        net = build_network(_BROKEN_CONFIG)
        net.set_interface_state("eth0", "up")
        ok, _ = net.ping("10.0.0.1")
        assert ok  # connectivity fine
        assert net.resolve("svc.local") is None  # but DNS still fails

    def test_mutation_state_roundtrip(self):
        net = build_network(_BROKEN_CONFIG)
        net.set_interface_state("eth0", "up")
        net.set_interface_address("eth0", "10.0.0.5", 24)
        net.set_default_gateway("10.0.0.1")
        snapshot = net.to_dict()

        fresh = build_network(_BROKEN_CONFIG)  # rebuilt from static (broken) config
        assert fresh.student.interfaces[0].state == "DOWN"
        fresh.apply_state(snapshot)
        assert fresh.student.interfaces[0].state == "UP"
        assert fresh.student.interfaces[0].ip == "10.0.0.5"
        assert fresh.default_gateway() == "10.0.0.1"


# ═══════════════════════════════════════════
# ip command — simulated fixes
# ═══════════════════════════════════════════
class TestIpFixCommands:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.network = build_network(_BROKEN_CONFIG)
        return sh

    def test_link_set_up(self):
        sh = self._shell()
        out = sh.execute("ip link set eth0 up")
        assert out == ""
        assert sh.network.student.interfaces[0].state == "UP"

    def test_link_set_unknown_iface(self):
        sh = self._shell()
        out = sh.execute("ip link set wlan0 up")
        assert "not found" in out

    def test_addr_add_replaces_ip(self):
        sh = self._shell()
        out = sh.execute("ip addr add 10.0.0.5/24 dev eth0")
        assert out == ""
        assert sh.network.student.interfaces[0].ip == "10.0.0.5"
        assert sh.network.student.interfaces[0].cidr == 24

    def test_addr_add_bad_spec(self):
        sh = self._shell()
        out = sh.execute("ip addr add nocidr dev eth0")
        assert "usage" in out

    def test_route_add_default(self):
        sh = self._shell()
        out = sh.execute("ip route add default via 10.0.0.1")
        assert out == ""
        assert sh.network.default_gateway() == "10.0.0.1"

    def test_route_add_missing_via(self):
        sh = self._shell()
        out = sh.execute("ip route add default")
        assert "usage" in out

    def test_never_touches_real_os(self):
        # No socket/subprocess/etc. *import* anywhere in the module under
        # test — these commands can only mutate the in-memory VirtualNetwork.
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
        forbidden = {"socket", "subprocess", "requests", "urllib", "http", "os"}
        assert not (imported & forbidden), f"forbidden imports found: {imported & forbidden}"


# ═══════════════════════════════════════════
# Validator — network_state
# ═══════════════════════════════════════════
class TestNetworkStateValidator:
    def test_interface_state_pass(self):
        sh = Shell()
        sh.network = build_network(_BROKEN_CONFIG)
        sh.network.set_interface_state("eth0", "up")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "network_state", "check": "interface_state",
            "interface": "eth0", "match": "UP"}}
        assert validate(obj, sh).passed

    def test_interface_state_fail(self):
        sh = Shell()
        sh.network = build_network(_BROKEN_CONFIG)
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "network_state", "check": "interface_state",
            "interface": "eth0", "match": "UP"}}
        assert not validate(obj, sh).passed

    def test_interface_ip_pass(self):
        sh = Shell()
        sh.network = build_network(_BROKEN_CONFIG)
        sh.network.set_interface_address("eth0", "10.0.0.5", 24)
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "network_state", "check": "interface_ip",
            "interface": "eth0", "match": "10.0.0.5"}}
        assert validate(obj, sh).passed

    def test_default_gateway_pass(self):
        sh = Shell()
        sh.network = build_network(_BROKEN_CONFIG)
        sh.network.set_default_gateway("10.0.0.1")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "network_state", "check": "default_gateway", "match": "10.0.0.1"}}
        assert validate(obj, sh).passed

    def test_no_network_configured(self):
        sh = Shell()
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "network_state", "check": "default_gateway", "match": "10.0.0.1"}}
        assert not validate(obj, sh).passed

    def test_unknown_check(self):
        sh = Shell()
        sh.network = build_network(_BROKEN_CONFIG)
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "network_state", "check": "bogus", "match": "x"}}
        assert not validate(obj, sh).passed


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "network-troubleshooting" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("network-troubleshooting")
        assert m is not None
        assert m["title"] == "Network Troubleshooting"
        assert m["xp_total"] == 350

    def test_objective_count(self):
        m = get_mission("network-troubleshooting")
        assert len(m["objectives"]) == 14

    def test_xp_sums_to_total(self):
        m = get_mission("network-troubleshooting")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_chained_after_networking_fundamentals(self):
        assert MISSIONS["networking-fundamentals"]["next_mission"] == "network-troubleshooting"

    def test_starts_broken(self):
        m = get_mission("network-troubleshooting")
        eth0 = m["network"]["hosts"]["10.10.10.20"]["interfaces"][0]
        assert eth0["state"] == "DOWN"
        assert eth0["ip"] == "10.10.20.50"
        assert m["network"]["dns_working"] is False


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("network-troubleshooting", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 350
        assert set(r.progress.completed_ids) == {f"nt-{i}" for i in range(1, 15)}

    def test_identify_down_objective_requires_seeing_it_while_still_broken(self):
        r = MissionRunner("network-troubleshooting", 2)
        assert "nt-3" not in r.progress.completed_ids
        r.execute("ip link")
        assert "nt-3" in r.progress.completed_ids  # saw 'state DOWN' for real

    def test_identify_down_cannot_complete_after_already_fixed(self):
        # If the student fixes the interface first, the DOWN state no
        # longer exists to observe — nt-3 correctly stays incomplete.
        r = MissionRunner("network-troubleshooting", 20)
        r.execute("ip link set eth0 up")
        r.execute("ip link")
        assert "nt-2" in r.progress.completed_ids  # ran the inspection command
        assert "nt-3" not in r.progress.completed_ids  # but never actually saw it down

    def test_dns_objective_requires_connectivity_and_broken_dns(self):
        r = MissionRunner("network-troubleshooting", 3)
        r.execute("ip link set eth0 up")
        r.execute("ip addr add 10.10.10.20/24 dev eth0")
        r.execute("ip route add default via 10.10.10.1")
        result = r.execute("nslookup example.local")
        assert "NXDOMAIN" in result["output"]
        assert "nt-13" in r.progress.completed_ids

    def test_progress_partial(self):
        r = MissionRunner("network-troubleshooting", 4)
        r.execute("ping 10.10.10.1")
        assert len(r.progress.completed_ids) == 1
        assert not r.progress.completed

    def test_hint(self):
        r = MissionRunner("network-troubleshooting", 5)
        hint = r.use_hint("nt-4")
        assert "ip link set" in hint
        assert r.progress.hints_used == 1

    def test_ai_context_reflects_live_network_state(self):
        r = MissionRunner("network-troubleshooting", 6)
        ctx = r.ai_context()
        assert ctx["network"]["interface_state"] == "DOWN"
        r.execute("ip link set eth0 up")
        ctx2 = r.ai_context()
        assert ctx2["network"]["interface_state"] == "UP"

    def test_save_restore_preserves_fixes(self):
        r = MissionRunner("network-troubleshooting", 7)
        r.execute("ip link set eth0 up")
        r.execute("ip addr add 10.10.10.20/24 dev eth0")
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        assert r2.network_status()["interface_state"] == "UP"
        assert r2.network_status()["interface_ip"] == "10.10.10.20/24"
        assert "nt-4" in r2.progress.completed_ids
        assert "nt-7" in r2.progress.completed_ids

    def test_fresh_session_is_isolated_from_prior_fixes(self):
        r1 = MissionRunner("network-troubleshooting", 8)
        r1.execute("ip link set eth0 up")
        r2 = MissionRunner("network-troubleshooting", 9)
        assert r2.network_status()["interface_state"] == "DOWN"


# ═══════════════════════════════════════════
# Services — status/chain, persistence, real XP engine, no-hints bonus
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
        u = User(username="nettrouble_test", email="nettrouble@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "nettrouble_test", uid


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
]


class TestServices:
    def test_full_chain_unlocks_and_completes_with_real_xp_and_bonus(self, app, student):
        _uname, uid = student
        with app.app_context():
            from app.auth.models import User
            from app.core.missions import (
                dashboard_stats,
                execute_command,
                mission_status,
                start_mission,
            )

            assert mission_status(uid, "network-troubleshooting") == "locked"

            for slug, commands in _PREREQ_MISSIONS:
                start_mission(uid, slug)
                for c in commands:
                    execute_command(uid, slug, c)

            assert mission_status(uid, "network-troubleshooting") == "available"

            start_mission(uid, "network-troubleshooting")
            for c in SOLVE:
                execute_command(uid, "network-troubleshooting", c)

            assert mission_status(uid, "network-troubleshooting") == "completed"

            user = User.query.get(uid)
            # 200+200+250+300+350 = 1300 base, plus a 10% no-hints bonus on
            # every mission solved without calling get_hint (all of them here).
            assert user.xp > 1300
            assert user.level > 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] == 5
            assert stats["xp_earned"] > 1300


# ═══════════════════════════════════════════
# HTTP — discovery/detail pick up the new mission automatically
# ═══════════════════════════════════════════
class TestHTTP:
    def test_discover_page_lists_network_troubleshooting(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
            assert b"Network Troubleshooting" in r.data

    def test_detail_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/network-troubleshooting")
            assert r.status_code == 200
            assert b"Systematic troubleshooting" in r.data

    def test_terminal_page_shows_network_status_panel(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/network-troubleshooting")
            assert r.status_code == 200
            assert b"tm-netstatus" in r.data

    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "network-troubleshooting" in ids
