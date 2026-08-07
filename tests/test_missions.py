"""Tests for YC-034.2 — Interactive Linux Missions."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0342-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_missions.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions import (
    ai_context,
    available_missions,
    execute_command,
    get_hint,
    get_progress,
    reset_mission,
    start_mission,
)
from app.core.missions.mission_loader import get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell


# ═══════════════════════════════════════════
# Loader
# ═══════════════════════════════════════════
class TestLoader:
    def test_get_mission(self):
        m = get_mission("linux-basics")
        assert m is not None
        assert m["title"] == "Linux Basics"
        assert len(m["objectives"]) == 8

    def test_list_missions(self):
        missions = available_missions()
        assert len(missions) >= 1

    def test_unknown(self):
        assert get_mission("nonexistent") is None


# ═══════════════════════════════════════════
# Validator
# ═══════════════════════════════════════════
class TestValidator:
    def test_command_match(self):
        m = get_mission("linux-basics")
        obj = m["objectives"][0]  # pwd
        sh = Shell()
        r = validate(obj, sh, "pwd", "/home/student")
        assert r.passed

    def test_command_fail(self):
        m = get_mission("linux-basics")
        obj = m["objectives"][0]
        sh = Shell()
        r = validate(obj, sh, "ls", "Documents")
        assert not r.passed

    def test_cwd_match(self):
        m = get_mission("linux-basics")
        obj = m["objectives"][3]  # cd Documents
        sh = Shell()
        sh.execute("cd Documents")
        r = validate(obj, sh, "cd Documents", "")
        assert r.passed

    def test_file_exists(self):
        m = get_mission("linux-basics")
        obj = m["objectives"][5]  # touch notes.txt
        sh = Shell()
        sh.execute("touch notes.txt")
        r = validate(obj, sh, "touch notes.txt", "")
        assert r.passed


# ═══════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════
class TestRunner:
    def test_create(self):
        r = MissionRunner("linux-basics", 1)
        assert r.progress.total == 8
        cur = r.current_objective()
        assert cur["title"] == "Where am I?"

    def test_execute_validates(self):
        r = MissionRunner("linux-basics", 1)
        result = r.execute("pwd")
        assert len(result["validations"]) >= 1
        assert result["validations"][0]["passed"]
        assert "lb-1" in r.progress.completed_ids

    def test_full_mission(self):
        r = MissionRunner("linux-basics", 2)
        r.execute("pwd")
        r.execute("ls")
        r.execute("ls -la")
        r.execute("cd Documents")
        r.execute("cat welcome.txt")
        r.shell.execute("cd ~")
        r.execute("touch notes.txt")
        r.execute("mkdir practice")
        r.execute("history")
        assert r.progress.completed
        assert r.progress.xp_earned >= 160  # may get bonus from multi-match

    def test_hint(self):
        r = MissionRunner("linux-basics", 3)
        hint = r.use_hint("lb-1")
        assert len(hint) > 5
        assert r.progress.hints_used == 1

    def test_ai_context(self):
        r = MissionRunner("linux-basics", 4)
        ctx = r.ai_context()
        assert ctx["mission"] == "Linux Basics"
        assert ctx["current_objective"] == "Where am I?"

    def test_save_restore(self):
        r = MissionRunner("linux-basics", 5)
        r.execute("pwd")
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        assert "lb-1" in r2.progress.completed_ids
        assert r2.progress.xp_earned >= 20


# ═══════════════════════════════════════════
# Services
# ═══════════════════════════════════════════
class TestServices:
    def test_start(self):
        r = start_mission(100, "linux-basics")
        assert r["mission"]["title"] == "Linux Basics"

    def test_start_unknown(self):
        r = start_mission(100, "nope")
        assert "error" in r

    def test_execute(self):
        start_mission(101, "linux-basics")
        r = execute_command(101, "linux-basics", "pwd")
        assert r["output"] == "/home/student"
        assert len(r["validations"]) >= 1

    def test_hint(self):
        start_mission(102, "linux-basics")
        r = get_hint(102, "linux-basics", "lb-1")
        assert len(r["hint"]) > 5

    def test_progress(self):
        start_mission(103, "linux-basics")
        execute_command(103, "linux-basics", "pwd")
        p = get_progress(103, "linux-basics")
        assert p is not None
        assert "lb-1" in p["progress"]["completed_ids"]

    def test_reset(self):
        start_mission(104, "linux-basics")
        execute_command(104, "linux-basics", "pwd")
        r = reset_mission(104, "linux-basics")
        assert r["progress"]["completed_ids"] == []

    def test_ai_context(self):
        start_mission(105, "linux-basics")
        ctx = ai_context(105, "linux-basics")
        assert ctx["mission"] == "Linux Basics"


# ═══════════════════════════════════════════
# HTTP
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
        u = User(username="mission_test", email="mt@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
    yield "mission_test"


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


class TestHTTP:
    def test_mission_page(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            r = c.get("/terminal/mission/linux-basics")
            assert r.status_code == 200
            assert b"Linux Basics" in r.data

    def test_api_start(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            r = c.post("/api/terminal/mission/start",
                        json={"slug": "linux-basics"})
            assert r.status_code == 200
            assert r.get_json()["mission"]["title"] == "Linux Basics"

    def test_api_execute(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            c.post("/api/terminal/mission/start",
                   json={"slug": "linux-basics"})
            r = c.post("/api/terminal/mission/execute",
                        json={"slug": "linux-basics", "command": "pwd"})
            assert r.status_code == 200
            data = r.get_json()
            assert data["output"] == "/home/student"
            assert len(data["validations"]) >= 1

    def test_api_hint(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            c.post("/api/terminal/mission/start",
                   json={"slug": "linux-basics"})
            r = c.post("/api/terminal/mission/hint",
                        json={"slug": "linux-basics",
                              "objective_id": "lb-1"})
            assert r.status_code == 200
            assert len(r.get_json()["hint"]) > 5

    def test_api_missions_list(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            assert len(r.get_json()) >= 1

    def test_api_reset(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            r = c.post("/api/terminal/mission/reset",
                        json={"slug": "linux-basics"})
            assert r.status_code == 200
