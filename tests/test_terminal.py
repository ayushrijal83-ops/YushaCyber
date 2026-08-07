"""Tests for YC-034.1 — Browser Linux Terminal."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0341-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_term.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.terminal import (
    execute,
    reset_shell,
    shell_context,
    start_shell,
)
from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.shell import Shell


# ═══════════════════════════════════════════
# Filesystem
# ═══════════════════════════════════════════
class TestFS:
    def test_default_tree(self):
        fs = VirtualFS()
        assert fs.isdir("/home/student")
        assert fs.isfile("/etc/passwd")

    def test_listdir(self):
        fs = VirtualFS()
        items = fs.listdir("/home/student")
        assert "Documents" in items

    def test_read(self):
        fs = VirtualFS()
        c = fs.read("/etc/hostname")
        assert "yushacyber" in c

    def test_write(self):
        fs = VirtualFS()
        fs.write("/tmp/test.txt", "hello")
        assert fs.read("/tmp/test.txt") == "hello"

    def test_mkdir(self):
        fs = VirtualFS()
        assert fs.mkdir("/home/student/evidence")
        assert fs.isdir("/home/student/evidence")

    def test_touch(self):
        fs = VirtualFS()
        assert fs.touch("/tmp/new.txt")
        assert fs.isfile("/tmp/new.txt")

    def test_rm(self):
        fs = VirtualFS()
        fs.touch("/tmp/del.txt")
        assert fs.rm("/tmp/del.txt")
        assert not fs.exists("/tmp/del.txt")

    def test_cd(self):
        fs = VirtualFS()
        assert fs.cd("/etc")
        assert fs.cwd == "/etc"
        assert fs.cd("..")
        assert fs.cwd == "/"

    def test_cd_fail(self):
        fs = VirtualFS()
        assert not fs.cd("/nonexistent")

    def test_tree(self):
        fs = VirtualFS()
        t = fs.tree("/etc", depth=1)
        assert "passwd" in t

    def test_roundtrip(self):
        fs = VirtualFS()
        fs.cd("/tmp")
        fs.write("/tmp/x.txt", "data")
        d = fs.to_dict()
        fs2 = VirtualFS.from_dict(d)
        assert fs2.cwd == "/tmp"
        assert fs2.read("/tmp/x.txt") == "data"

    def test_no_real_access(self):
        fs = VirtualFS()
        assert fs.read("/real/file") is None


# ═══════════════════════════════════════════
# Shell
# ═══════════════════════════════════════════
class TestShell:
    def test_pwd(self):
        sh = Shell()
        assert sh.execute("pwd") == "/home/student"

    def test_ls(self):
        sh = Shell()
        out = sh.execute("ls")
        assert "Documents" in out

    def test_ls_la(self):
        sh = Shell()
        out = sh.execute("ls -la")
        assert "drwxr-xr-x" in out

    def test_cd(self):
        sh = Shell()
        sh.execute("cd /etc")
        assert sh.fs.cwd == "/etc"

    def test_cd_fail(self):
        sh = Shell()
        out = sh.execute("cd /nope")
        assert "No such file or directory" in out

    def test_cat(self):
        sh = Shell()
        out = sh.execute("cat /etc/hostname")
        assert "yushacyber" in out

    def test_cat_missing(self):
        sh = Shell()
        out = sh.execute("cat /nope.txt")
        assert "No such file or directory" in out

    def test_echo(self):
        sh = Shell()
        assert sh.execute("echo hello") == "hello"

    def test_echo_redirect(self):
        sh = Shell()
        sh.execute("echo test > /tmp/out.txt")
        assert sh.fs.read("/tmp/out.txt") == "test\n"

    def test_mkdir(self):
        sh = Shell()
        sh.execute("mkdir evidence")
        assert sh.fs.isdir("/home/student/evidence")

    def test_touch(self):
        sh = Shell()
        sh.execute("touch notes.txt")
        assert sh.fs.isfile("/home/student/notes.txt")

    def test_rm(self):
        sh = Shell()
        sh.execute("touch /tmp/del.txt")
        out = sh.execute("rm /tmp/del.txt")
        assert out == ""
        assert not sh.fs.exists("/tmp/del.txt")

    def test_whoami(self):
        sh = Shell()
        assert sh.execute("whoami") == "student"

    def test_hostname(self):
        sh = Shell()
        assert sh.execute("hostname") == "yushacyber-lab"

    def test_date(self):
        sh = Shell()
        assert "2026" in sh.execute("date")

    def test_history(self):
        sh = Shell()
        sh.execute("pwd")
        sh.execute("ls")
        out = sh.execute("history")
        assert "pwd" in out and "ls" in out

    def test_help(self):
        sh = Shell()
        out = sh.execute("help")
        assert "pwd" in out and "cat" in out

    def test_grep(self):
        sh = Shell()
        out = sh.execute("grep root /etc/passwd")
        assert "root" in out

    def test_find(self):
        sh = Shell()
        out = sh.execute("find /etc -name passwd")
        assert "/etc/passwd" in out

    def test_tree_cmd(self):
        sh = Shell()
        out = sh.execute("tree /etc")
        assert "passwd" in out

    def test_id(self):
        sh = Shell()
        assert "student" in sh.execute("id")

    def test_uname(self):
        sh = Shell()
        assert "Linux" in sh.execute("uname -a")

    def test_unknown(self):
        sh = Shell()
        out = sh.execute("hacktheplanet")
        assert "command not found" in out

    def test_prompt(self):
        sh = Shell()
        assert "student@lab" in sh.prompt

    def test_roundtrip(self):
        sh = Shell()
        sh.execute("cd /etc")
        sh.execute("pwd")
        d = sh.to_dict()
        sh2 = Shell.from_dict(d)
        assert sh2.fs.cwd == "/etc"
        assert "pwd" in sh2.history

    def test_autocomplete(self):
        sh = Shell()
        matches = sh.complete("pw")
        assert "pwd" in matches


# ═══════════════════════════════════════════
# Services
# ═══════════════════════════════════════════
class TestServices:
    def test_start(self):
        r = start_shell(99, "test")
        assert "prompt" in r

    def test_execute(self):
        start_shell(100, "test")
        r = execute(100, "test", "pwd")
        assert r["output"] == "/home/student"

    def test_reset(self):
        start_shell(101, "test")
        execute(101, "test", "cd /etc")
        r = reset_shell(101, "test")
        assert "prompt" in r

    def test_context(self):
        start_shell(102, "test")
        execute(102, "test", "ls")
        ctx = shell_context(102, "test")
        assert ctx["last_command"] == "ls"


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
        u = User(username="term_test", email="tt@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
    yield "term_test"


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"}, follow_redirects=True)


class TestHTTP:
    def test_terminal_page(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            r = c.get("/terminal")
            assert r.status_code == 200
            assert b"terminal" in r.data.lower()

    def test_api_start(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            r = c.post("/api/terminal/start", json={"slug": "test"})
            assert r.status_code == 200

    def test_api_execute(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            c.post("/api/terminal/start", json={"slug": "test"})
            r = c.post("/api/terminal/execute",
                        json={"slug": "test", "command": "pwd"})
            assert r.status_code == 200
            assert r.get_json()["output"] == "/home/student"

    def test_api_complete(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            c.post("/api/terminal/start", json={"slug": "test"})
            r = c.post("/api/terminal/complete",
                        json={"slug": "test", "partial": "pw"})
            assert r.status_code == 200
            assert "pwd" in r.get_json()["matches"]

    def test_api_reset(self, app, student):
        with app.test_client() as c:
            _login(c, student)
            r = c.post("/api/terminal/reset", json={"slug": "test"})
            assert r.status_code == 200
