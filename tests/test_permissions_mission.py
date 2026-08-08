"""Tests for YC-034.3 — Interactive Missions UI + Linux Permissions mission."""

from __future__ import annotations

import os
import tempfile
from typing import ClassVar

_TMPDIR = tempfile.mkdtemp(prefix="yc0343-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_permissions.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.shell import Shell


# ═══════════════════════════════════════════
# Loader
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_exists(self):
        m = get_mission("linux-permissions")
        assert m is not None
        assert m["title"] == "Linux Permissions"
        assert m["difficulty"] == "Beginner"
        assert m["xp_total"] == 200

    def test_objective_count(self):
        m = get_mission("linux-permissions")
        assert len(m["objectives"]) == 8

    def test_xp_sums_to_total(self):
        m = get_mission("linux-permissions")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_has_learn_list(self):
        m = get_mission("linux-permissions")
        assert "chmod" in m["learn"]

    def test_chained_after_basics(self):
        assert MISSIONS["linux-basics"]["next_mission"] == "linux-permissions"

    def test_seed_files_have_initial_permissions(self):
        m = get_mission("linux-permissions")
        perms = m["permissions"]
        assert perms["/home/student/permissions/private.txt"]["owner"] == "root"
        assert perms["/home/student/permissions/challenge.txt"]["mode"] == "000"


# ═══════════════════════════════════════════
# Filesystem permission metadata
# ═══════════════════════════════════════════
class TestFSPermissions:
    def test_default_mode(self):
        fs = VirtualFS()
        fs.touch("/tmp/a.txt")
        assert fs.get_mode("/tmp/a.txt") == "644"
        assert fs.get_mode("/tmp") == "755"

    def test_set_mode(self):
        fs = VirtualFS()
        fs.touch("/tmp/a.txt")
        assert fs.set_mode("/tmp/a.txt", "600")
        assert fs.get_mode("/tmp/a.txt") == "600"

    def test_set_mode_missing_file(self):
        fs = VirtualFS()
        assert not fs.set_mode("/tmp/nope.txt", "600")

    def test_owner_default_and_set(self):
        fs = VirtualFS()
        fs.touch("/tmp/a.txt")
        assert fs.get_owner("/tmp/a.txt") == "student"
        fs.set_owner("/tmp/a.txt", "root")
        assert fs.get_owner("/tmp/a.txt") == "root"
        assert fs.get_group("/tmp/a.txt") == "root"

    def test_can_read(self):
        fs = VirtualFS()
        fs.touch("/tmp/a.txt")
        assert fs.can_read("/tmp/a.txt", "student")
        fs.set_mode("/tmp/a.txt", "600")
        fs.set_owner("/tmp/a.txt", "root")
        assert not fs.can_read("/tmp/a.txt", "student")
        assert fs.can_read("/tmp/a.txt", "root")

    def test_mode_to_symbolic(self):
        assert VirtualFS.mode_to_symbolic("755", True) == "drwxr-xr-x"
        assert VirtualFS.mode_to_symbolic("644", False) == "-rw-r--r--"
        assert VirtualFS.mode_to_symbolic("000", False) == "----------"

    def test_roundtrip_preserves_meta(self):
        fs = VirtualFS()
        fs.touch("/tmp/a.txt")
        fs.set_mode("/tmp/a.txt", "600")
        d = fs.to_dict()
        fs2 = VirtualFS.from_dict(d)
        assert fs2.get_mode("/tmp/a.txt") == "600"

    def test_permissions_seeded_on_construction(self):
        fs = VirtualFS(tree={"tmp": {"secret.txt": "x"}},
                       permissions={"/tmp/secret.txt": {"mode": "600", "owner": "root"}})
        assert fs.get_mode("/tmp/secret.txt") == "600"
        assert fs.get_owner("/tmp/secret.txt") == "root"


# ═══════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════
class TestCommands:
    def test_groups(self):
        sh = Shell()
        assert "student" in sh.execute("groups")

    def test_chmod(self):
        sh = Shell()
        sh.execute("touch a.txt")
        out = sh.execute("chmod 600 a.txt")
        assert out == ""
        assert sh.fs.get_mode("a.txt") == "600"

    def test_chmod_missing_file(self):
        sh = Shell()
        out = sh.execute("chmod 600 nope.txt")
        assert "cannot access" in out

    def test_chmod_bad_mode(self):
        sh = Shell()
        sh.execute("touch a.txt")
        out = sh.execute("chmod rwx a.txt")
        assert "invalid mode" in out

    def test_chown(self):
        sh = Shell()
        sh.execute("touch a.txt")
        out = sh.execute("chown root a.txt")
        assert out == ""
        assert sh.fs.get_owner("a.txt") == "root"
        assert sh.fs.get_group("a.txt") == "root"

    def test_chown_with_group(self):
        sh = Shell()
        sh.execute("touch a.txt")
        sh.execute("chown root:wheel a.txt")
        assert sh.fs.get_owner("a.txt") == "root"
        assert sh.fs.get_group("a.txt") == "wheel"

    def test_cat_permission_denied(self):
        sh = Shell()
        sh.execute("touch secret.txt")
        sh.fs.set_mode("secret.txt", "600")
        sh.fs.set_owner("secret.txt", "root")
        out = sh.execute("cat secret.txt")
        assert "Permission denied" in out

    def test_cat_allowed_after_chown(self):
        sh = Shell()
        sh.execute("touch secret.txt")
        sh.fs.set_mode("secret.txt", "600")
        sh.fs.set_owner("secret.txt", "root")
        sh.execute("chown student secret.txt")
        out = sh.execute("cat secret.txt")
        assert "Permission denied" not in out

    def test_ls_l_single_file(self):
        sh = Shell()
        sh.execute("touch a.txt")
        out = sh.execute("ls -l a.txt")
        assert "rw-r--r--" in out
        assert "a.txt" in out

    def test_ls_l_shows_real_perms(self):
        sh = Shell()
        sh.execute("touch a.txt")
        sh.fs.set_mode("a.txt", "600")
        out = sh.execute("ls -la")
        assert "rw-------" in out

    def test_ls_still_works_default(self):
        # Existing linux-basics behavior must be unaffected.
        sh = Shell()
        out = sh.execute("ls -la")
        assert "drwxr-xr-x" in out


# ═══════════════════════════════════════════
# Validator
# ═══════════════════════════════════════════
class TestValidator:
    def test_file_mode_pass(self):
        sh = Shell()
        sh.execute("touch a.txt")
        sh.fs.set_mode("a.txt", "644")
        obj = {"id": "x", "xp": 10,
               "validate": {"type": "file_mode", "match": "644", "path": "/home/student/a.txt"}}
        r = validate(obj, sh)
        assert r.passed

    def test_file_mode_fail(self):
        sh = Shell()
        sh.execute("touch a.txt")
        obj = {"id": "x", "xp": 10,
               "validate": {"type": "file_mode", "match": "600", "path": "/home/student/a.txt"}}
        r = validate(obj, sh)
        assert not r.passed

    def test_file_owner_pass(self):
        sh = Shell()
        sh.execute("touch a.txt")
        sh.fs.set_owner("a.txt", "root")
        obj = {"id": "x", "xp": 10,
               "validate": {"type": "file_owner", "match": "root", "path": "/home/student/a.txt"}}
        r = validate(obj, sh)
        assert r.passed

    def test_file_owner_fail(self):
        sh = Shell()
        sh.execute("touch a.txt")
        obj = {"id": "x", "xp": 10,
               "validate": {"type": "file_owner", "match": "root", "path": "/home/student/a.txt"}}
        r = validate(obj, sh)
        assert not r.passed


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    SOLVE: ClassVar[list[str]] = [
        "cd permissions", "ls -l", "whoami", "id", "groups",
        "cat private.txt", "chmod 644 challenge.txt",
        "ls -l challenge.txt", "chown student private.txt",
    ]

    def test_complete_solve(self):
        r = MissionRunner("linux-permissions", 1)
        for c in self.SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 200

    def test_cannot_be_gamed_from_wrong_directory(self):
        r = MissionRunner("linux-permissions", 2)
        for c in self.SOLVE[1:]:  # skip 'cd permissions'
            r.execute(c)
        assert not r.progress.completed
        # lp-1..lp-4 (command-only checks) still pass regardless of cwd.
        assert {"lp-1", "lp-2", "lp-3", "lp-4"} <= set(r.progress.completed_ids)
        # lp-6/7/8 require real filesystem state and must NOT be gamed.
        assert "lp-6" not in r.progress.completed_ids
        assert "lp-8" not in r.progress.completed_ids

    def test_private_file_unreadable_until_chown(self):
        r = MissionRunner("linux-permissions", 3)
        r.execute("cd permissions")
        out = r.execute("cat private.txt")["output"]
        assert "Permission denied" in out
        r.execute("chown student private.txt")
        out2 = r.execute("cat private.txt")["output"]
        assert "Permission denied" not in out2


# ═══════════════════════════════════════════
# Services — status, stats, XP/DB persistence
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
        u = User(username="perm_test", email="permtest@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "perm_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


class TestServicesStatus:
    def test_locked_then_unlocked_then_completed_with_real_xp(self, app, student):
        _uname, uid = student
        with app.app_context():
            from app.auth.models import User
            from app.core.missions import (
                dashboard_stats,
                execute_command,
                list_missions_with_status,
                mission_status,
                start_mission,
            )

            # 1. Permissions mission starts locked; basics is available.
            assert mission_status(uid, "linux-permissions") == "locked"
            assert mission_status(uid, "linux-basics") == "available"

            # 2. Complete linux-basics.
            start_mission(uid, "linux-basics")
            for c in ["pwd", "ls", "ls -la", "cd Documents", "cat welcome.txt"]:
                execute_command(uid, "linux-basics", c)
            execute_command(uid, "linux-basics", "cd ~")
            for c in ["touch notes.txt", "mkdir practice", "history"]:
                execute_command(uid, "linux-basics", c)

            assert mission_status(uid, "linux-basics") == "completed"
            assert mission_status(uid, "linux-permissions") == "available"

            # 3. Complete linux-permissions.
            start_mission(uid, "linux-permissions")
            for c in TestFullRun.SOLVE:
                execute_command(uid, "linux-permissions", c)
            assert mission_status(uid, "linux-permissions") == "completed"

            missions = list_missions_with_status(uid)
            by_id = {m["id"]: m for m in missions}
            assert by_id["linux-basics"]["status"] == "completed"
            assert by_id["linux-permissions"]["status"] == "completed"

            # 4. XP went through the real dashboard XP/level engine, not a bypass.
            user = User.query.get(uid)
            assert user.xp >= 400
            assert user.level > 1
            stats = dashboard_stats(uid)
            assert stats["completed_missions"] == 2
            assert stats["xp_earned"] >= 400


# ═══════════════════════════════════════════
# HTTP — discovery + detail pages, mission terminal page
# ═══════════════════════════════════════════
class TestHTTP:
    def test_discover_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
            assert b"Interactive Cyber Labs" in r.data

    def test_detail_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/linux-permissions")
            assert r.status_code == 200
            assert b"Linux Permissions" in r.data

    def test_detail_page_unknown_404(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/does-not-exist")
            assert r.status_code == 404

    def test_discover_requires_login(self, app):
        with app.test_client() as c:
            r = c.get("/interactive-labs", follow_redirects=False)
            assert r.status_code in (302, 401)

    def test_mission_terminal_page_has_ui_markup(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/linux-permissions")
            assert r.status_code == 200
            for marker in (b"tm-mhead", b"data-tm-timer", b"data-tm-complete",
                          b"data-tm-restart", b"data-tm-exit"):
                assert marker in r.data

    def test_api_missions_list_includes_permissions(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "linux-permissions" in ids
