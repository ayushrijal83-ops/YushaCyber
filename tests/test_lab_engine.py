"""Tests for YC-034.0 — Interactive Cyber Labs (Browser Lab Engine)."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0340-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_labeng.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.lab_engine import state
from app.lab_engine.filesystem import VirtualFS
from app.lab_engine.models import get_lab
from app.lab_engine.objectives import Objective
from app.lab_engine.progress import LabProgress
from app.lab_engine.services import (
    available_labs,
    execute_command,
    reset_lab,
    start_lab,
)
from app.lab_engine.simulator import LabSimulator
from app.lab_engine.terminal import Terminal
from app.lab_engine.validator import (
    validate_answer,
    validate_command,
    validate_file,
)


# ===========================================================================
# Virtual Filesystem
# ===========================================================================
class TestFilesystem:
    def test_default_tree(self):
        fs = VirtualFS()
        assert fs.isdir("/home/student")
        assert fs.isfile("/etc/passwd")

    def test_listdir(self):
        fs = VirtualFS()
        items = fs.listdir("/home/student")
        assert "notes.txt" in items

    def test_read_file(self):
        fs = VirtualFS()
        content = fs.read("/home/student/notes.txt")
        assert "notes" in content.lower()

    def test_write_file(self):
        fs = VirtualFS()
        fs.write("/home/student/test.txt", "hello")
        assert fs.read("/home/student/test.txt") == "hello"

    def test_mkdir(self):
        fs = VirtualFS()
        assert fs.mkdir("/home/student/evidence")
        assert fs.isdir("/home/student/evidence")

    def test_remove(self):
        fs = VirtualFS()
        fs.write("/tmp/del.txt", "x")
        assert fs.remove("/tmp/del.txt")
        assert not fs.exists("/tmp/del.txt")

    def test_copy(self):
        fs = VirtualFS()
        assert fs.copy("/etc/passwd", "/tmp/passwd_copy")
        assert fs.isfile("/tmp/passwd_copy")

    def test_move(self):
        fs = VirtualFS()
        fs.write("/tmp/mv.txt", "data")
        assert fs.move("/tmp/mv.txt", "/tmp/moved.txt")
        assert fs.isfile("/tmp/moved.txt")
        assert not fs.exists("/tmp/mv.txt")

    def test_cd(self):
        fs = VirtualFS()
        assert fs.cd("/etc")
        assert fs.cwd == "/etc"
        assert fs.cd("..")
        assert fs.cwd == "/"

    def test_tree(self):
        fs = VirtualFS()
        output = fs.tree("/etc", depth=1)
        assert "passwd" in output

    def test_serialize(self):
        fs = VirtualFS()
        fs.cd("/tmp")
        d = fs.to_dict()
        fs2 = VirtualFS.from_dict(d)
        assert fs2.cwd == "/tmp"

    def test_no_real_fs_access(self):
        """Ensure we never touch real files."""
        fs = VirtualFS()
        assert fs.read("/real/system/file") is None


# ===========================================================================
# Terminal
# ===========================================================================
class TestTerminal:
    def test_pwd(self):
        t = Terminal()
        assert t.execute("pwd") == "/home/student"

    def test_ls(self):
        t = Terminal()
        output = t.execute("ls")
        assert "notes.txt" in output

    def test_cat(self):
        t = Terminal()
        output = t.execute("cat notes.txt")
        assert "notes" in output.lower()

    def test_cd(self):
        t = Terminal()
        t.execute("cd /etc")
        assert t.fs.cwd == "/etc"

    def test_grep(self):
        t = Terminal()
        output = t.execute("grep root /etc/passwd")
        assert "root" in output

    def test_mkdir(self):
        t = Terminal()
        t.execute("mkdir evidence")
        assert t.fs.isdir("/home/student/evidence")

    def test_echo(self):
        t = Terminal()
        output = t.execute("echo hello world")
        assert output == "hello world"

    def test_echo_redirect(self):
        t = Terminal()
        t.execute("echo test > /tmp/out.txt")
        assert t.fs.read("/tmp/out.txt") == "test\n"

    def test_whoami(self):
        t = Terminal()
        assert t.execute("whoami") == "student"

    def test_unknown_command(self):
        t = Terminal()
        output = t.execute("hacktheplanet")
        assert "command not found" in output

    def test_history(self):
        t = Terminal()
        t.execute("pwd")
        t.execute("ls")
        output = t.execute("history")
        assert "pwd" in output
        assert "ls" in output

    def test_windows_mode(self):
        t = Terminal(mode="windows")
        output = t.execute("dir")
        assert "notes.txt" in output
        output2 = t.execute("ipconfig")
        assert "10.0.0.50" in output2

    def test_serialize(self):
        t = Terminal()
        t.execute("pwd")
        d = t.to_dict()
        t2 = Terminal.from_dict(d)
        assert "pwd" in t2.history

    def test_find(self):
        t = Terminal()
        output = t.execute("find /etc -name passwd")
        assert "/etc/passwd" in output


# ===========================================================================
# Validator
# ===========================================================================
class TestValidator:
    def test_command_exact_match(self):
        obj = Objective(id="t1", expected="ls", validation_type="command")
        r = validate_command(obj, "ls")
        assert r.passed

    def test_command_partial_match(self):
        obj = Objective(id="t2", expected="cat notes.txt",
                        validation_type="command")
        r = validate_command(obj, "cat notes.txt")
        assert r.passed

    def test_command_fail(self):
        obj = Objective(id="t3", expected="pwd",
                        validation_type="command")
        r = validate_command(obj, "ls")
        assert not r.passed

    def test_answer_exact(self):
        obj = Objective(id="t4", expected="192.168.1.1",
                        validation_type="answer")
        r = validate_answer(obj, "192.168.1.1")
        assert r.passed

    def test_answer_fail(self):
        obj = Objective(id="t5", expected="admin",
                        validation_type="answer")
        r = validate_answer(obj, "root")
        assert not r.passed

    def test_file_exists(self):
        obj = Objective(id="t6", expected="/etc/passwd",
                        validation_type="file")
        fs = VirtualFS()
        r = validate_file(obj, fs)
        assert r.passed

    def test_file_missing(self):
        obj = Objective(id="t7", expected="/nope.txt",
                        validation_type="file")
        fs = VirtualFS()
        r = validate_file(obj, fs)
        assert not r.passed


# ===========================================================================
# Progress
# ===========================================================================
class TestProgress:
    def test_complete_objective(self):
        p = LabProgress(total_objectives=3)
        assert p.complete_objective("o1", 50)
        assert p.pct == pytest.approx(0.33, abs=0.01)
        assert not p.completed

    def test_auto_complete(self):
        p = LabProgress(total_objectives=2)
        p.complete_objective("o1", 50)
        p.complete_objective("o2", 50)
        assert p.completed
        assert p.xp_earned == 100

    def test_no_double_complete(self):
        p = LabProgress(total_objectives=2)
        p.complete_objective("o1", 50)
        assert not p.complete_objective("o1", 50)


# ===========================================================================
# Simulator
# ===========================================================================
class TestSimulator:
    def test_execute_and_validate(self):
        lab = get_lab("linux-basics")
        sim = LabSimulator(lab, user_id=1)
        result = sim.execute("pwd")
        assert result["output"] == "/home/student"
        assert len(result["validations"]) >= 1
        assert result["validations"][0]["passed"]

    def test_full_lab_completion(self):
        lab = get_lab("linux-basics")
        sim = LabSimulator(lab, user_id=2)
        sim.execute("pwd")
        sim.execute("ls")
        sim.execute("cat notes.txt")
        sim.execute("mkdir evidence")
        assert sim.progress.completed

    def test_serialize_restore(self):
        lab = get_lab("linux-basics")
        sim = LabSimulator(lab, user_id=3)
        sim.execute("pwd")
        d = sim.to_dict()
        sim2 = LabSimulator.from_dict(d, lab)
        assert "lb-1" in sim2.progress.completed_objectives


# ===========================================================================
# State
# ===========================================================================
class TestState:
    def test_save_load(self):
        state.save(99, "test-lab", {"progress": {"xp": 100}})
        loaded = state.load(99, "test-lab")
        assert loaded["progress"]["xp"] == 100
        state.reset(99, "test-lab")
        assert state.load(99, "test-lab") is None


# ===========================================================================
# Services
# ===========================================================================
class TestServices:
    def test_available_labs(self):
        labs = available_labs()
        assert len(labs) >= 3
        slugs = [l["slug"] for l in labs]
        assert "linux-basics" in slugs

    def test_start_lab(self):
        r = start_lab(100, "linux-basics")
        assert "lab" in r
        assert r["lab"]["slug"] == "linux-basics"

    def test_execute_command(self):
        start_lab(101, "linux-basics")
        r = execute_command(101, "linux-basics", "pwd")
        assert r["output"] == "/home/student"

    def test_reset_lab(self):
        start_lab(102, "linux-basics")
        execute_command(102, "linux-basics", "pwd")
        r = reset_lab(102, "linux-basics")
        assert r["progress"]["completed_objectives"] == []

    def test_unknown_lab(self):
        r = start_lab(103, "nonexistent")
        assert "error" in r


# ===========================================================================
# HTTP API
# ===========================================================================
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
    yield application


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        u = User(username="lab_eng_test", email="le@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
    yield "lab_eng_test"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestHTTP:
    def test_list_labs(self, app):
        with app.test_client() as client:
            r = client.get("/api/lab-engine/labs")
            assert r.status_code == 200
            assert len(r.get_json()) >= 3

    def test_start_lab(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.post("/api/lab-engine/start",
                            json={"slug": "linux-basics"})
            assert r.status_code == 200
            assert r.get_json()["lab"]["slug"] == "linux-basics"

    def test_execute(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.post("/api/lab-engine/start",
                        json={"slug": "linux-basics"})
            r = client.post("/api/lab-engine/execute",
                            json={"slug": "linux-basics",
                                  "command": "pwd"})
            assert r.status_code == 200
            assert r.get_json()["output"] == "/home/student"

    def test_reset(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.post("/api/lab-engine/start",
                        json={"slug": "linux-basics"})
            r = client.post("/api/lab-engine/reset",
                            json={"slug": "linux-basics"})
            assert r.status_code == 200

    def test_security_no_shell(self, app, student):
        """Commands are simulated — no real shell access."""
        with app.test_client() as client:
            _login(client, student)
            client.post("/api/lab-engine/start",
                        json={"slug": "linux-basics"})
            r = client.post("/api/lab-engine/execute",
                            json={"slug": "linux-basics",
                                  "command": "rm -rf /"})
            # Should not crash the server.
            assert r.status_code == 200
