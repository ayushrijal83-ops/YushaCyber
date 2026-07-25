"""Tests for YC-031.0 — Universal Scenario Engine.

Covers every engine module with pure unit tests (no app context
needed) plus integration tests confirming backward compatibility
with the existing Lab/LabObjective ORM + validator pipeline.
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0310-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_engines.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.engines import (  # noqa: E402
    objective_engine,
    progress_engine,
    scenario_engine,
    validation_engine,
)
from app.labs.simulator_base import Action  # noqa: E402
from app.labs.validator import ValidationContext  # noqa: E402


# ===========================================================================
# Scenario engine
# ===========================================================================
class TestScenarioEngine:
    def test_scenario_from_dict(self):
        s = scenario_engine.scenario_from_dict({
            "slug": "test-lab", "title": "Test",
            "difficulty": "Hard", "xp_reward": 100,
            "objectives": [
                {"id": 1, "title": "O1", "is_optional": False},
                {"id": 2, "title": "O2", "is_optional": True},
            ],
        })
        assert s.slug == "test-lab"
        assert s.difficulty == "Hard"
        assert len(s.objectives) == 2

    def test_is_complete_requires_non_optional(self):
        s = scenario_engine.scenario_from_dict({
            "objectives": [
                {"id": 1, "is_optional": False},
                {"id": 2, "is_optional": True},
            ],
        })
        assert scenario_engine.is_complete(s, {1}) is True
        assert scenario_engine.is_complete(s, {2}) is False
        assert scenario_engine.is_complete(s, set()) is False

    def test_completion_ratio(self):
        s = scenario_engine.scenario_from_dict({
            "objectives": [
                {"id": 1, "is_optional": False},
                {"id": 2, "is_optional": False},
                {"id": 3, "is_optional": True},
            ],
        })
        assert scenario_engine.completion_ratio(s, {1}) == 0.5
        assert scenario_engine.completion_ratio(s, {1, 2}) == 1.0
        assert scenario_engine.completion_ratio(s, set()) == 0.0

    def test_to_dict_roundtrip(self):
        s = scenario_engine.Scenario(slug="x", title="X", xp_reward=50)
        d = s.to_dict()
        assert d["slug"] == "x"
        assert d["xp_reward"] == 50


# ===========================================================================
# Objective engine
# ===========================================================================
class TestObjectiveEngine:
    def test_visit_panel(self):
        vtype, vdata = objective_engine.visit_panel("sources")
        assert vtype == "event_emitted"
        assert vdata["event"] == "sources_visited"

    def test_inspect_evidence(self):
        vtype, vdata = objective_engine.inspect_evidence()
        assert vtype == "event_emitted"
        assert vdata["event"] == "all_evidence_inspected"

    def test_execute_command(self):
        vtype, vdata = objective_engine.execute_command("nmap -sV target")
        assert vtype == "exact_command"
        assert vdata["command"] == "nmap -sV target"

    def test_answer_question(self):
        vtype, vdata = objective_engine.answer_question(
            "checks.ip", True)
        assert vtype == "state_flag"
        assert vdata["equals"] is True

    def test_submit_report(self):
        vtype, vdata = objective_engine.submit_report()
        assert vtype == "event_emitted"

    def test_multi_step(self):
        steps = objective_engine.multi_step(
            ["a_done", "b_done", "c_done"])
        assert len(steps) == 3
        assert all(s[0] == "event_emitted" for s in steps)

    def test_custom_hook(self):
        vtype, vdata = objective_engine.custom_hook(
            "my_validator", {"key": "val"})
        assert vtype == "my_validator"
        assert vdata["key"] == "val"

    def test_build_objective(self):
        obj = objective_engine.build_objective(
            "Test objective", "Do the thing",
            objective_engine.submit_report(),
            xp=25, order=3, hints=["h1", "h2"])
        assert obj["title"] == "Test objective"
        assert obj["validator_type"] == "event_emitted"
        assert obj["xp_reward"] == 25
        assert obj["hint1"] == "h1"
        assert obj["hint2"] == "h2"
        assert obj["hint3"] is None


# ===========================================================================
# Validation engine — new validator types
# ===========================================================================
def _ctx(state=None, events=None, command=""):
    return ValidationContext(
        action=Action(type="command",
                      payload={"command": command}),
        state=state or {},
        events=events or [])


class TestExactMatch:
    def test_match(self):
        ctx = _ctx(state={"answer": "203.0.113.50"})
        assert validation_engine.validate(
            "exact_match",
            {"path": "answer", "expected": "203.0.113.50"}, ctx)

    def test_case_insensitive(self):
        ctx = _ctx(state={"answer": "HELLO"})
        assert validation_engine.validate(
            "exact_match",
            {"path": "answer", "expected": "hello"}, ctx)

    def test_mismatch(self):
        ctx = _ctx(state={"answer": "wrong"})
        assert not validation_engine.validate(
            "exact_match",
            {"path": "answer", "expected": "right"}, ctx)

    def test_missing_path(self):
        ctx = _ctx(state={})
        assert not validation_engine.validate(
            "exact_match",
            {"path": "missing", "expected": "x"}, ctx)


class TestMultiStep:
    def test_all_events_present(self):
        ctx = _ctx(events=[
            {"type": "a"}, {"type": "b"}, {"type": "c"}])
        assert validation_engine.validate(
            "multi_step", {"events": ["a", "b", "c"]}, ctx)

    def test_missing_event_fails(self):
        ctx = _ctx(events=[{"type": "a"}, {"type": "c"}])
        assert not validation_engine.validate(
            "multi_step", {"events": ["a", "b", "c"]}, ctx)

    def test_empty_required_passes(self):
        ctx = _ctx()
        assert validation_engine.validate(
            "multi_step", {"events": []}, ctx)


class TestOrderedTasks:
    def test_correct_order(self):
        ctx = _ctx(events=[
            {"type": "a"}, {"type": "x"}, {"type": "b"},
            {"type": "c"}])
        assert validation_engine.validate(
            "ordered_tasks", {"events": ["a", "b", "c"]}, ctx)

    def test_wrong_order_fails(self):
        ctx = _ctx(events=[
            {"type": "c"}, {"type": "b"}, {"type": "a"}])
        assert not validation_engine.validate(
            "ordered_tasks", {"events": ["a", "b", "c"]}, ctx)


class TestScoreThreshold:
    def test_meets_threshold(self):
        ctx = _ctx(state={"score": {"total": 80}})
        assert validation_engine.validate(
            "score_threshold",
            {"path": "score.total", "min": 50}, ctx)

    def test_below_threshold(self):
        ctx = _ctx(state={"score": {"total": 30}})
        assert not validation_engine.validate(
            "score_threshold",
            {"path": "score.total", "min": 50}, ctx)


class TestCustomHook:
    def test_missing_function(self):
        ctx = _ctx()
        assert not validation_engine.validate(
            "custom_hook", {"function": ""}, ctx)

    def test_nonexistent_module(self):
        ctx = _ctx()
        assert not validation_engine.validate(
            "custom_hook",
            {"function": "nonexistent.module.func"}, ctx)


# ===========================================================================
# Progress engine
# ===========================================================================
class TestProgressEngine:
    def _scenario(self):
        return scenario_engine.scenario_from_dict({
            "slug": "test",
            "objectives": [
                {"id": 1, "title": "A", "is_optional": False,
                 "xp_reward": 10},
                {"id": 2, "title": "B", "is_optional": False,
                 "xp_reward": 20},
                {"id": 3, "title": "C", "is_optional": True,
                 "xp_reward": 5},
            ],
        })

    def test_not_started(self):
        p = progress_engine.compute_progress(self._scenario(), set())
        assert p.status == "not_started"
        assert p.ratio == 0.0
        assert p.current_objective["title"] == "A"

    def test_in_progress(self):
        p = progress_engine.compute_progress(self._scenario(), {1})
        assert p.status == "in_progress"
        assert p.ratio == 0.5
        assert p.current_objective["title"] == "B"

    def test_completed(self):
        p = progress_engine.compute_progress(self._scenario(), {1, 2})
        assert p.status == "completed"
        assert p.ratio == 1.0
        assert p.current_objective is None

    def test_objectives_summary(self):
        summary = progress_engine.objectives_summary(
            self._scenario(), {1})
        assert len(summary) == 3
        assert summary[0]["completed"] is True
        assert summary[1]["completed"] is False
        assert summary[2]["optional"] is True

    def test_to_dict(self):
        p = progress_engine.compute_progress(self._scenario(), {1})
        d = p.to_dict()
        assert d["scenario_slug"] == "test"
        assert d["completed_required"] == 1


# ===========================================================================
# Integration: scenario_from_lab with real ORM (backward compatibility)
# ===========================================================================
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
        from app.labs.forensics.seed import seed_forensics_labs
        seed_forensics_labs()
    yield application


class TestBackwardCompatibility:
    def test_scenario_from_lab_forensics(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="forensics-fundamentals").first()
            assert lab is not None
            s = scenario_engine.scenario_from_lab(lab)
            assert s.slug == "forensics-fundamentals"
            assert s.difficulty == "Easy"
            assert s.xp_reward == 50
            assert len(s.objectives) == 5
            assert s.objectives[0]["validator_type"] in (
                "event_emitted", "state_flag")

    def test_scenario_from_lab_soc(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="soc-analyst-fundamentals").first()
            assert lab is not None
            s = scenario_engine.scenario_from_lab(lab)
            assert s.slug == "soc-analyst-fundamentals"
            assert s.xp_reward == 150

    def test_existing_validators_still_work(self, app):
        """Ensure the five new validators didn't break the old ones."""
        from app.labs.validator import VALIDATOR_REGISTRY
        old = ["exact_command", "regex_command", "output_contains",
               "state_flag", "event_emitted"]
        for name in old:
            assert name in VALIDATOR_REGISTRY, f"{name} missing!"
        new = ["exact_match", "multi_step", "ordered_tasks",
               "score_threshold", "custom_hook"]
        for name in new:
            assert name in VALIDATOR_REGISTRY, f"{name} missing!"

    def test_progress_from_real_lab(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="forensics-fundamentals").first()
            s = scenario_engine.scenario_from_lab(lab)
            p = progress_engine.compute_progress(s, set())
            assert p.status == "not_started"
            assert p.total_objectives == 5
            p2 = progress_engine.compute_progress(
                s, {o["id"] for o in s.objectives
                    if not o.get("is_optional")})
            assert p2.status == "completed"
            assert p2.ratio == 1.0
