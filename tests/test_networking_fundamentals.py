"""Tests for YC-034.5 — Networking Fundamentals interactive mission."""

from __future__ import annotations

import os
import tempfile
from typing import ClassVar

_TMPDIR = tempfile.mkdtemp(prefix="yc0345-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_networking.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.terminal.network import build_network
from app.core.terminal.shell import Shell

# ═══════════════════════════════════════════
# Network simulator (framework-level, mission-agnostic)
# ═══════════════════════════════════════════
_TEST_CONFIG = {
    "student_ip": "10.0.0.5",
    "dns_server_ip": "10.0.0.53",
    "hosts": {
        "10.0.0.5": {
            "hostname": "test-pc",
            "interfaces": [{"name": "eth0", "ip": "10.0.0.5", "cidr": 24, "state": "UP"}],
            "routes": [{"destination": "default", "via": "10.0.0.1",
                       "dev": "eth0", "is_default": True}],
            "services": [{"port": 22, "proto": "tcp", "name": "ssh"}],
        },
        "10.0.0.1": {"hostname": "gw", "reachable": True},
        "10.0.0.99": {"hostname": "down-host", "reachable": False},
    },
    "dns_records": [{"hostname": "svc.local", "ip": "10.0.0.1"}],
}


class TestNetworkSimulator:
    def test_build_network(self):
        net = build_network(_TEST_CONFIG)
        assert net.student_ip == "10.0.0.5"
        assert net.student.hostname == "test-pc"

    def test_interfaces_text(self):
        net = build_network(_TEST_CONFIG)
        text = net.interfaces_text()
        assert "eth0" in text and "10.0.0.5/24" in text

    def test_route_text_shows_default(self):
        net = build_network(_TEST_CONFIG)
        text = net.route_text()
        assert "default via 10.0.0.1" in text

    def test_default_gateway(self):
        net = build_network(_TEST_CONFIG)
        assert net.default_gateway() == "10.0.0.1"

    def test_ping_reachable_host(self):
        net = build_network(_TEST_CONFIG)
        ok, out = net.ping("10.0.0.1")
        assert ok
        assert "64 bytes from 10.0.0.1" in out
        assert "0% packet loss" in out

    def test_ping_unreachable_host(self):
        net = build_network(_TEST_CONFIG)
        ok, out = net.ping("10.0.0.99")
        assert not ok
        assert "100% packet loss" in out

    def test_ping_unknown_host_is_unreachable_not_a_crash(self):
        net = build_network(_TEST_CONFIG)
        ok, out = net.ping("8.8.8.8")
        assert not ok
        assert "100% packet loss" in out

    def test_resolve_known_hostname(self):
        net = build_network(_TEST_CONFIG)
        assert net.resolve("svc.local") == "10.0.0.1"

    def test_resolve_unknown_hostname(self):
        net = build_network(_TEST_CONFIG)
        assert net.resolve("nope.local") is None

    def test_is_port_open(self):
        net = build_network(_TEST_CONFIG)
        assert net.is_port_open("10.0.0.5", 22)
        assert not net.is_port_open("10.0.0.5", 9999)

    def test_services_text(self):
        net = build_network(_TEST_CONFIG)
        text = net.services_text()
        assert "10.0.0.5:22" in text
        assert "ssh" in text


# ═══════════════════════════════════════════
# Terminal commands — fully simulated
# ═══════════════════════════════════════════
class TestNetworkingCommands:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.network = build_network(_TEST_CONFIG)
        return sh

    def test_no_network_configured(self):
        sh = Shell()  # network defaults to None for every other mission
        assert sh.execute("ip addr") == "ip: no network configured for this session"
        assert sh.execute("ping 10.0.0.1") == "ping: no network configured for this session"

    def test_ip_addr(self):
        sh = self._shell()
        out = sh.execute("ip addr")
        assert "10.0.0.5/24" in out

    def test_ip_route(self):
        sh = self._shell()
        out = sh.execute("ip route")
        assert "default via 10.0.0.1" in out

    def test_ip_link(self):
        sh = self._shell()
        out = sh.execute("ip link")
        assert "eth0" in out

    def test_ip_unknown_subcommand(self):
        sh = self._shell()
        out = sh.execute("ip bogus")
        assert "unknown sub-command" in out

    def test_ping_by_ip(self):
        sh = self._shell()
        out = sh.execute("ping 10.0.0.1")
        assert "64 bytes from 10.0.0.1" in out

    def test_ping_by_hostname_resolves_first(self):
        sh = self._shell()
        out = sh.execute("ping svc.local")
        assert "64 bytes from 10.0.0.1" in out

    def test_ping_no_target(self):
        sh = self._shell()
        out = sh.execute("ping")
        assert "Destination address required" in out

    def test_ss_lists_local_services(self):
        sh = self._shell()
        out = sh.execute("ss")
        assert "10.0.0.5:22" in out

    def test_nslookup_resolves(self):
        sh = self._shell()
        out = sh.execute("nslookup svc.local")
        assert "Address: 10.0.0.1" in out
        assert "Server:" in out

    def test_nslookup_nxdomain(self):
        sh = self._shell()
        out = sh.execute("nslookup nope.local")
        assert "NXDOMAIN" in out

    def test_host_resolves(self):
        sh = self._shell()
        out = sh.execute("host svc.local")
        assert "10.0.0.1" in out

    def test_host_nxdomain(self):
        sh = self._shell()
        out = sh.execute("host nope.local")
        assert "NXDOMAIN" in out


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "networking-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("networking-fundamentals")
        assert m is not None
        assert m["title"] == "Networking Fundamentals"
        assert m["difficulty"] == "Beginner"
        assert m["xp_total"] == 300

    def test_objective_count(self):
        m = get_mission("networking-fundamentals")
        assert len(m["objectives"]) == 12

    def test_xp_sums_to_total(self):
        m = get_mission("networking-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_chained_after_bash_fundamentals(self):
        assert MISSIONS["bash-fundamentals"]["next_mission"] == "networking-fundamentals"

    def test_network_config_present(self):
        m = get_mission("networking-fundamentals")
        assert m["network"]["student_ip"] == "10.10.10.20"
        assert "10.10.10.1" in m["network"]["hosts"]

    def test_hosts_file_seeded(self):
        m = get_mission("networking-fundamentals")
        hosts_content = m["filesystem"]["etc"]["hosts"]
        assert "10.10.10.20" in hosts_content


# ═══════════════════════════════════════════
# Full mission run via MissionRunner
# ═══════════════════════════════════════════
class TestFullRun:
    SOLVE: ClassVar[list[str]] = [
        "ip addr", "ip route", "ping 10.10.10.1", "ping 10.10.10.10",
        "ss", "nslookup example.local", "cat /etc/hosts", "ping 10.10.10.30",
    ]

    def test_complete_solve(self):
        r = MissionRunner("networking-fundamentals", 1)
        for c in self.SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 300
        assert set(r.progress.completed_ids) == {f"net-{i}" for i in range(1, 13)}

    def test_hosts_file_objective_not_gamed_by_nslookup(self):
        r = MissionRunner("networking-fundamentals", 2)
        r.execute("nslookup example.local")
        assert "net-10" not in r.progress.completed_ids
        r.execute("cat /etc/hosts")
        assert "net-10" in r.progress.completed_ids

    def test_pinging_outside_topology_never_completes_objectives(self):
        r = MissionRunner("networking-fundamentals", 3)
        result = r.execute("ping 8.8.8.8")
        assert "100% packet loss" in result["output"]
        assert result["validations"] == []

    def test_progress_partial(self):
        r = MissionRunner("networking-fundamentals", 4)
        r.execute("ip addr")
        r.execute("ip route")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) == 4  # net-1..net-4 all output-adjacent
        assert r.progress.pct == int(4 / 12 * 100)

    def test_hint(self):
        r = MissionRunner("networking-fundamentals", 5)
        hint = r.use_hint("net-5")
        assert "ping" in hint.lower()
        assert r.progress.hints_used == 1

    def test_ai_context_includes_network_summary(self):
        r = MissionRunner("networking-fundamentals", 6)
        ctx = r.ai_context()
        assert ctx["network"]["interface_ip"] == "10.10.10.20/24"
        assert ctx["network"]["default_gateway"] == "10.10.10.1"

    def test_save_restore_reattaches_network(self):
        r = MissionRunner("networking-fundamentals", 7)
        r.execute("ip addr")
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        assert r2.shell.network is not None
        out = r2.shell.execute("ping 10.10.10.1")
        assert "64 bytes from 10.10.10.1" in out
        assert "net-1" in r2.progress.completed_ids


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
        u = User(username="net_test", email="nettest@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "net_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


class TestServices:
    def test_locked_until_bash_done_then_completes_with_real_xp(self, app, student):
        _uname, uid = student
        with app.app_context():
            from app.auth.models import User
            from app.core.missions import (
                dashboard_stats,
                execute_command,
                mission_status,
                start_mission,
            )

            assert mission_status(uid, "networking-fundamentals") == "locked"

            start_mission(uid, "linux-basics")
            for c in ["pwd", "ls", "ls -la", "cd Documents", "cat welcome.txt"]:
                execute_command(uid, "linux-basics", c)
            execute_command(uid, "linux-basics", "cd ~")
            for c in ["touch notes.txt", "mkdir practice", "history"]:
                execute_command(uid, "linux-basics", c)

            start_mission(uid, "linux-permissions")
            for c in ["cd permissions", "ls -l", "whoami", "id", "groups",
                     "cat private.txt", "chmod 644 challenge.txt",
                     "ls -l challenge.txt", "chown student private.txt"]:
                execute_command(uid, "linux-permissions", c)

            start_mission(uid, "bash-fundamentals")
            for c in ["cd bash-lab", 'name="student"', 'echo "$name"',
                     'export LAB="yushacyber"', 'echo "$LAB"', "current=$(pwd)",
                     "ls | grep txt", "ls > output.txt",
                     '''echo 'echo "Hello from YushaCyber!"' > script.sh''',
                     "chmod +x script.sh", "./script.sh",
                     'if [ -f script.sh ]; then echo "found"; fi',
                     'for i in 1 2 3; do echo "count-$i"; done']:
                execute_command(uid, "bash-fundamentals", c)

            assert mission_status(uid, "networking-fundamentals") == "available"

            start_mission(uid, "networking-fundamentals")
            for c in TestFullRun.SOLVE:
                execute_command(uid, "networking-fundamentals", c)

            assert mission_status(uid, "networking-fundamentals") == "completed"

            user = User.query.get(uid)
            assert user.xp >= 950  # 200 + 200 + 250 + 300 across all four missions
            assert user.level > 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] == 4
            assert stats["xp_earned"] >= 950


# ═══════════════════════════════════════════
# HTTP — discovery/detail pick up the new mission automatically
# ═══════════════════════════════════════════
class TestHTTP:
    def test_discover_page_lists_networking_fundamentals(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
            assert b"Networking Fundamentals" in r.data

    def test_detail_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/networking-fundamentals")
            assert r.status_code == 200
            assert b"Default gateway" in r.data

    def test_api_missions_list_includes_networking(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "networking-fundamentals" in ids
