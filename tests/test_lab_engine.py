"""Tests for YC-034.0 — Interactive Cyber Lab Engine Foundation."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0340-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_labeng.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.lab_engine import (
    LabDef,
    LabObjectiveDef,
    LabType,
    Workspace,
    available_labs,
    available_types,
    get_ai_context,
    get_session,
    register_lab,
    register_workspace,
    reset_lab,
    start_lab,
    submit_objective,
    use_hint,
)
from app.core.lab_engine.events import EventLog
from app.core.lab_engine.objective import check
from app.core.lab_engine.progress import LabProgress
from app.core.lab_engine.registry import clear as reg_clear
from app.core.lab_engine.session import LabSession
from app.core.lab_engine.state import (
    clear_all as state_clear,
)
from app.core.lab_engine.state import (
    exists as state_exists,
)
from app.core.lab_engine.state import (
    load,
    save,
)
from app.core.lab_engine.state import (
    reset as state_reset,
)

SAMPLE_LAB = LabDef(
    slug="test-lab", title="Test Lab",
    lab_type="linux", difficulty="Easy", xp_total=100,
    objectives=[
        LabObjectiveDef(id="o1", title="Run pwd", kind="run_command",
                        expected="pwd", xp=25, order=1),
        LabObjectiveDef(id="o2", title="Find the flag",
                        kind="capture_flag",
                        expected="flag{test123}", xp=50, order=2),
        LabObjectiveDef(id="o3", title="Answer",
                        kind="answer_question",
                        expected="42", xp=25, order=3),
    ],
)


@pytest.fixture(autouse=True)
def _clean():
    reg_clear()
    state_clear()
    register_lab(SAMPLE_LAB)
    yield
    reg_clear()
    state_clear()


# ===========================================================================
# Types
# ===========================================================================
class TestTypes:
    def test_lab_type_enum(self):
        assert LabType.LINUX.value == "linux"
        assert LabType.WEB.value == "web"
        assert LabType.FORENSICS.value == "forensics"

    def test_lab_def_to_dict(self):
        d = SAMPLE_LAB.to_dict()
        assert d["slug"] == "test-lab"
        assert len(d["objectives"]) == 3

    def test_objective_to_dict(self):
        d = SAMPLE_LAB.objectives[0].to_dict()
        assert d["kind"] == "run_command"
        assert d["xp"] == 25

    def test_workspace_roundtrip(self):
        ws = Workspace(workspace_type="terminal",
                       config={"shell": "bash"},
                       state={"cwd": "/home"})
        d = ws.to_dict()
        ws2 = Workspace.from_dict(d)
        assert ws2.workspace_type == "terminal"
        assert ws2.state["cwd"] == "/home"


# ===========================================================================
# Registry
# ===========================================================================
class TestRegistry:
    def test_register_and_get(self):
        from app.core.lab_engine.registry import get_lab, list_labs
        assert get_lab("test-lab") is not None
        assert len(list_labs()) == 1

    def test_register_workspace_factory(self):
        def my_factory(config):
            return Workspace(workspace_type="custom", config=config)
        register_workspace("custom", my_factory)
        assert "custom" in available_types()

    def test_list_by_type(self):
        assert len(available_labs("linux")) == 1
        assert len(available_labs("web")) == 0


# ===========================================================================
# Objectives
# ===========================================================================
class TestObjectives:
    def test_run_command(self):
        r = check(SAMPLE_LAB.objectives[0], "pwd")
        assert r.passed
        assert r.xp_earned == 25

    def test_capture_flag(self):
        r = check(SAMPLE_LAB.objectives[1], "flag{test123}")
        assert r.passed
        assert r.xp_earned == 50

    def test_capture_flag_wrong(self):
        r = check(SAMPLE_LAB.objectives[1], "flag{wrong}")
        assert not r.passed

    def test_answer_question(self):
        r = check(SAMPLE_LAB.objectives[2], "42")
        assert r.passed

    def test_answer_wrong(self):
        r = check(SAMPLE_LAB.objectives[2], "99")
        assert not r.passed


# ===========================================================================
# Events
# ===========================================================================
class TestEvents:
    def test_emit_and_recent(self):
        log = EventLog()
        log.emit("student_joined", {"user_id": 1})
        log.emit("objective_completed", {"id": "o1"})
        assert log.count() == 2
        assert log.recent(1)[0]["kind"] == "objective_completed"

    def test_roundtrip(self):
        log = EventLog()
        log.emit("test", {"a": 1})
        log2 = EventLog.from_list(log.to_list())
        assert log2.count() == 1


# ===========================================================================
# Progress
# ===========================================================================
class TestProgress:
    def test_complete(self):
        p = LabProgress(total_objectives=3)
        assert p.complete("o1", 25)
        assert p.pct == pytest.approx(0.33, abs=0.01)
        assert not p.completed

    def test_full_completion(self):
        p = LabProgress(total_objectives=2)
        p.complete("o1", 25)
        p.complete("o2", 50)
        assert p.completed
        assert p.xp_earned == 75

    def test_no_double(self):
        p = LabProgress(total_objectives=2)
        p.complete("o1", 25)
        assert not p.complete("o1", 25)

    def test_hints_and_attempts(self):
        p = LabProgress(total_objectives=1)
        p.use_hint()
        p.add_attempt()
        assert p.hints_used == 1
        assert p.attempts == 1


# ===========================================================================
# State
# ===========================================================================
class TestState:
    def test_save_load(self):
        save(1, "test-lab", {"xp": 100})
        assert state_exists(1, "test-lab")
        assert load(1, "test-lab")["xp"] == 100

    def test_reset(self):
        save(1, "test-lab", {"xp": 100})
        state_reset(1, "test-lab")
        assert not state_exists(1, "test-lab")


# ===========================================================================
# Session
# ===========================================================================
class TestSession:
    def test_create(self):
        s = LabSession(SAMPLE_LAB, user_id=1)
        assert s.progress.started
        assert s.progress.total_objectives == 3

    def test_submit_pass(self):
        s = LabSession(SAMPLE_LAB, user_id=1)
        r = s.submit("o1", "pwd")
        assert r.passed
        assert "o1" in s.progress.completed_ids

    def test_submit_fail(self):
        s = LabSession(SAMPLE_LAB, user_id=1)
        r = s.submit("o1", "wrong")
        assert not r.passed

    def test_full_completion(self):
        s = LabSession(SAMPLE_LAB, user_id=1)
        s.submit("o1", "pwd")
        s.submit("o2", "flag{test123}")
        s.submit("o3", "42")
        assert s.progress.completed
        events = s.events.all()
        kinds = [e["kind"] for e in events]
        assert "lab_completed" in kinds

    def test_ai_context(self):
        s = LabSession(SAMPLE_LAB, user_id=1)
        ctx = s.ai_context()
        assert ctx["lab_slug"] == "test-lab"
        assert ctx["current_objective"]["id"] == "o1"

    def test_roundtrip(self):
        s = LabSession(SAMPLE_LAB, user_id=1)
        s.submit("o1", "pwd")
        d = s.to_dict()
        s2 = LabSession.from_dict(d, SAMPLE_LAB)
        assert "o1" in s2.progress.completed_ids
        assert s2.events.count() >= 1


# ===========================================================================
# Services (public API)
# ===========================================================================
class TestServices:
    def test_start_lab(self):
        r = start_lab(10, "test-lab")
        assert r["lab"]["slug"] == "test-lab"

    def test_start_unknown(self):
        r = start_lab(10, "nonexistent")
        assert "error" in r

    def test_submit_objective(self):
        start_lab(11, "test-lab")
        r = submit_objective(11, "test-lab", "o1", "pwd")
        assert r["passed"]

    def test_use_hint(self):
        start_lab(12, "test-lab")
        use_hint(12, "test-lab", "o1")
        s = get_session(12, "test-lab")
        assert s["progress"]["hints_used"] == 1

    def test_reset_lab(self):
        start_lab(13, "test-lab")
        submit_objective(13, "test-lab", "o1", "pwd")
        r = reset_lab(13, "test-lab")
        assert r["progress"]["completed_ids"] == []

    def test_ai_context(self):
        start_lab(14, "test-lab")
        ctx = get_ai_context(14, "test-lab")
        assert ctx["lab_slug"] == "test-lab"

    def test_available_labs(self):
        labs = available_labs()
        assert len(labs) >= 1
        assert labs[0]["slug"] == "test-lab"
