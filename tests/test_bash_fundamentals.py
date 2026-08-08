"""Tests for YC-034.4 — Bash Fundamentals interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0344-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_bash.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.shell import Shell

SOLVE = [
    "cd bash-lab",
    'name="student"',
    'echo "$name"',
    'export LAB="yushacyber"',
    'echo "$LAB"',
    "current=$(pwd)",
    "ls | grep txt",
    "ls > output.txt",
    '''echo 'echo "Hello from YushaCyber!"' > script.sh''',
    "chmod +x script.sh",
    "./script.sh",
    'if [ -f script.sh ]; then echo "found"; fi',
    'for i in 1 2 3; do echo "count-$i"; done',
]


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "bash-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("bash-fundamentals")
        assert m is not None
        assert m["title"] == "Bash Fundamentals"
        assert m["difficulty"] == "Beginner"
        assert m["xp_total"] == 250

    def test_objective_count(self):
        m = get_mission("bash-fundamentals")
        assert len(m["objectives"]) == 13

    def test_xp_sums_to_total(self):
        m = get_mission("bash-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_has_learn_list(self):
        m = get_mission("bash-fundamentals")
        assert "Pipes" in m["learn"]
        assert "Basic loops" in m["learn"]

    def test_chained_after_permissions(self):
        assert MISSIONS["linux-permissions"]["next_mission"] == "bash-fundamentals"

    def test_workspace_seeded(self):
        m = get_mission("bash-fundamentals")
        lab = m["filesystem"]["home"]["student"]["bash-lab"]
        assert "files.txt" in lab
        assert "notes.md" in lab


# ═══════════════════════════════════════════
# Shell engine — variables, expansion, pipes, redirection
# ═══════════════════════════════════════════
class TestShellVariables:
    def test_assignment_and_expansion(self):
        sh = Shell()
        sh.execute('name="student"')
        assert sh.vars["name"] == "student"
        out = sh.execute('echo "$name"')
        assert out == "student"

    def test_assignment_no_quotes(self):
        sh = Shell()
        sh.execute("name=student")
        assert sh.vars["name"] == "student"

    def test_export_makes_env_var(self):
        sh = Shell()
        sh.execute('export LAB="yushacyber"')
        assert sh.env["LAB"] == "yushacyber"
        out = sh.execute('echo "$LAB"')
        assert out == "yushacyber"

    def test_command_substitution(self):
        sh = Shell()
        sh.execute("current=$(pwd)")
        assert sh.vars["current"] == "/home/student"

    def test_undefined_variable_expands_empty(self):
        sh = Shell()
        out = sh.execute('echo "$nope"')
        assert out == ""


class TestShellPipesRedirection:
    def test_pipe_filters_output(self):
        fs = VirtualFS(tree={"home": {"student": {
            "files.txt": "a", "notes.md": "b"}}})
        sh = Shell(fs=fs)
        out = sh.execute("ls | grep txt")
        assert out == "files.txt"

    def test_pipe_no_match_is_empty(self):
        fs = VirtualFS(tree={"home": {"student": {
            "files.txt": "a", "notes.md": "b"}}})
        sh = Shell(fs=fs)
        out = sh.execute("ls | grep zzz")
        assert out == ""

    def test_redirect_creates_file(self):
        sh = Shell()
        out = sh.execute("ls > output.txt")
        assert out == ""
        assert sh.fs.isfile("output.txt")

    def test_redirect_append(self):
        sh = Shell()
        sh.execute("echo one > out.txt")
        sh.execute("echo two >> out.txt")
        assert sh.fs.read("out.txt") == "one\ntwo\n"


class TestShellScripts:
    def test_create_and_read_script(self):
        sh = Shell()
        sh.execute("""echo 'echo "Hello from YushaCyber!"' > script.sh""")
        assert "Hello from YushaCyber" in (sh.fs.read("script.sh") or "")

    def test_chmod_plus_x(self):
        sh = Shell()
        sh.execute("touch script.sh")
        sh.execute("chmod +x script.sh")
        assert sh.fs.get_mode("script.sh") == "755"

    def test_chmod_minus_x(self):
        sh = Shell()
        sh.execute("touch script.sh")
        sh.execute("chmod +x script.sh")
        sh.execute("chmod -x script.sh")
        assert sh.fs.get_mode("script.sh") == "644"

    def test_script_requires_executable_bit(self):
        sh = Shell()
        sh.execute("""echo 'echo "hi"' > script.sh""")
        out = sh.execute("./script.sh")
        assert "Permission denied" in out

    def test_script_executes_after_chmod(self):
        sh = Shell()
        sh.execute("""echo 'echo "Hello from YushaCyber!"' > script.sh""")
        sh.execute("chmod +x script.sh")
        out = sh.execute("./script.sh")
        assert "Hello from YushaCyber" in out

    def test_missing_script(self):
        sh = Shell()
        out = sh.execute("./nope.sh")
        assert "No such file or directory" in out


class TestShellConditionalsLoops:
    def test_if_true_branch(self):
        sh = Shell()
        sh.execute("touch script.sh")
        out = sh.execute('if [ -f script.sh ]; then echo "found"; fi')
        assert out == "found"

    def test_if_false_branch(self):
        sh = Shell()
        out = sh.execute('if [ -f nope.sh ]; then echo "found"; fi')
        assert out == ""

    def test_for_loop(self):
        sh = Shell()
        out = sh.execute('for i in 1 2 3; do echo "count-$i"; done')
        assert out == "count-1\ncount-2\ncount-3"


# ═══════════════════════════════════════════
# Full mission run via MissionRunner
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("bash-fundamentals", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 250
        assert set(r.progress.completed_ids) == {f"bf-{i}" for i in range(1, 14)}

    def test_progress_partial(self):
        r = MissionRunner("bash-fundamentals", 2)
        for c in SOLVE[:5]:
            r.execute(c)
        assert not r.progress.completed
        assert len(r.progress.completed_ids) == 5
        assert r.progress.pct == int(5 / 13 * 100)

    def test_cannot_run_script_before_chmod(self):
        r = MissionRunner("bash-fundamentals", 3)
        r.execute("cd bash-lab")
        r.execute('''echo 'echo "Hello from YushaCyber!"' > script.sh''')
        result = r.execute("./script.sh")
        assert "Permission denied" in result["output"]
        assert "bf-11" not in r.progress.completed_ids

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("bash-fundamentals", 10)
        r1.execute("cd bash-lab")
        r1.execute("touch leftover.txt")

        r2 = MissionRunner("bash-fundamentals", 11)
        r2.execute("cd bash-lab")
        out = r2.execute("ls")["output"]
        assert "leftover.txt" not in out

    def test_hint(self):
        r = MissionRunner("bash-fundamentals", 4)
        hint = r.use_hint("bf-2")
        assert "name=" in hint
        assert r.progress.hints_used == 1

    def test_save_restore_preserves_vars(self):
        r = MissionRunner("bash-fundamentals", 5)
        r.execute("cd bash-lab")
        r.execute('name="student"')
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        assert r2.shell.vars.get("name") == "student"
        assert r2.shell.fs.cwd == "/home/student/bash-lab"
        assert "bf-1" in r2.progress.completed_ids
        assert "bf-2" in r2.progress.completed_ids


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
        u = User(username="bash_test", email="bashtest@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "bash_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


class TestServices:
    def test_locked_until_permissions_done_then_completes_with_real_xp(self, app, student):
        _uname, uid = student
        with app.app_context():
            from app.auth.models import User
            from app.core.missions import (
                dashboard_stats,
                execute_command,
                mission_status,
                start_mission,
            )

            assert mission_status(uid, "bash-fundamentals") == "locked"

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

            assert mission_status(uid, "bash-fundamentals") == "available"

            start_mission(uid, "bash-fundamentals")
            for c in SOLVE:
                execute_command(uid, "bash-fundamentals", c)

            assert mission_status(uid, "bash-fundamentals") == "completed"

            user = User.query.get(uid)
            assert user.xp >= 650  # 200 + 200 + 250 across all three missions
            assert user.level > 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] == 3
            assert stats["xp_earned"] >= 650


# ═══════════════════════════════════════════
# HTTP — discovery/detail pick up the new mission automatically
# ═══════════════════════════════════════════
class TestHTTP:
    def test_discover_page_lists_bash_fundamentals(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
            assert b"Bash Fundamentals" in r.data

    def test_detail_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/bash-fundamentals")
            assert r.status_code == 200
            assert b"Command substitution" in r.data

    def test_api_missions_list_includes_bash_fundamentals(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "bash-fundamentals" in ids
