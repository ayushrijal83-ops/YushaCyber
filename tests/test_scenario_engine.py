"""Tests for YC-031.1 — Universal Scenario Engine (Core).

Covers every submodule: types, models, engine, validator, progress,
services. Plus backward-compatibility integration tests against
real ORM Lab rows.
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0311-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_core.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.core.scenario import (  # noqa: E402
    Difficulty,
    Grade,
    Objective,
    ObjectiveType,
    ReportType,
    Scenario,
    ValidationRule,
    calculate_progress,
    generate_report,
    load_scenario,
    validate_submission,
)
from app.core.scenario import engine  # noqa: E402
from app.core.scenario import models  # noqa: E402
from app.core.scenario import validator as val_mod  # noqa: E402
from app.core.scenario import progress as prog_mod  # noqa: E402


# ===========================================================================
# Types
# ===========================================================================
class TestTypes:
    def test_difficulty_enum(self):
        assert Difficulty.EASY.value == "Easy"
        assert Difficulty.EXPERT.value == "Expert"

    def test_grade_enum(self):
        assert Grade.EXCELLENT.value == "Excellent"
        assert Grade.FAIL.value == "Fail"

    def test_objective_types(self):
        assert ObjectiveType.VISIT_PAGE.value == "visit_page"
        assert ObjectiveType.IDENTIFY_IOC.value == "identify_ioc"

    def test_report_types(self):
        assert ReportType.INCIDENT.value == "incident"
        assert ReportType.ASSESSMENT.value == "assessment"

    def test_validation_rule_constructors(self):
        r = ValidationRule.exact_match("answer", "42")
        assert r.validator_type == "exact_match"
        assert r.data == {"path": "answer", "expected": "42"}

        r = ValidationRule.event_emitted("findings_correct")
        assert r.validator_type == "event_emitted"

        r = ValidationRule.multi_step(["a", "b"])
        assert r.data["events"] == ["a", "b"]

        r = ValidationRule.score_threshold("score.total", 50)
        assert r.data["min"] == 50

        r = ValidationRule.state_flag("checks.ip", True)
        assert r.data["equals"] is True

        r = ValidationRule.custom("my.module.func", key="val")
        assert r.validator_type == "custom_hook"
        assert r.data["key"] == "val"

    def test_validation_rule_roundtrip(self):
        r = ValidationRule("state_flag", {"path": "x", "equals": True})
        d = r.to_dict()
        r2 = ValidationRule.from_dict(d)
        assert r2.validator_type == "state_flag"
        assert r2.data["equals"] is True


# ===========================================================================
# Models
# ===========================================================================
class TestModels:
    def test_scenario_from_dict(self):
        s = models.scenario_from_dict({
            "slug": "test", "title": "T",
            "difficulty": "Hard", "xp_reward": 100,
            "objectives": [
                {"id": 1, "title": "O1", "is_optional": False,
                 "xp_reward": 20},
                {"id": 2, "title": "O2", "is_optional": True,
                 "xp_reward": 5},
            ],
        })
        assert s.slug == "test"
        assert len(s.objectives) == 2
        assert s.total_xp == 125
        assert len(s.required_objectives) == 1

    def test_scenario_to_dict(self):
        s = Scenario(slug="x", title="X", xp_reward=50)
        d = s.to_dict()
        assert d["slug"] == "x"
        assert d["xp_reward"] == 50

    def test_objective_to_dict(self):
        o = Objective(id=1, title="T",
                      validation=ValidationRule("state_flag", {"path": "x"}))
        d = o.to_dict()
        assert d["validation"]["validator_type"] == "state_flag"


# ===========================================================================
# Engine
# ===========================================================================
class TestEngine:
    def _scenario(self):
        return models.scenario_from_dict({
            "objectives": [
                {"id": 1, "is_optional": False, "xp_reward": 10},
                {"id": 2, "is_optional": False, "xp_reward": 20},
                {"id": 3, "is_optional": True, "xp_reward": 5},
            ],
            "xp_reward": 50,
        })

    def test_is_complete(self):
        s = self._scenario()
        assert engine.is_complete(s, {1, 2}) is True
        assert engine.is_complete(s, {1}) is False
        assert engine.is_complete(s, {1, 3}) is False

    def test_completion_ratio(self):
        s = self._scenario()
        assert engine.completion_ratio(s, {1}) == 0.5
        assert engine.completion_ratio(s, {1, 2}) == 1.0

    def test_next_objective(self):
        s = self._scenario()
        assert engine.next_objective(s, set()) == 1
        assert engine.next_objective(s, {1}) == 2
        assert engine.next_objective(s, {1, 2}) is None

    def test_compute_grade(self):
        assert engine.compute_grade(1.0, 1.0) == "Excellent"
        assert engine.compute_grade(0.8, 0.7) == "Good"
        assert engine.compute_grade(0.5, 0.5) == "Needs Improvement"
        assert engine.compute_grade(0.1, 0.1) == "Fail"

    def test_total_xp(self):
        s = self._scenario()
        assert engine.total_xp_available(s) == 85  # 50 + 10 + 20 + 5


# ===========================================================================
# Validator
# ===========================================================================
class TestValidator:
    def test_validate_state_flag(self):
        rule = ValidationRule.state_flag("answer", True)
        assert val_mod.validate(rule, {"answer": True}) is True
        assert val_mod.validate(rule, {"answer": False}) is False

    def test_validate_event_emitted(self):
        rule = ValidationRule.event_emitted("done")
        assert val_mod.validate(
            rule, {}, events=[{"type": "done"}]) is True
        assert val_mod.validate(rule, {}, events=[]) is False

    def test_validate_all(self):
        rules = [
            ValidationRule.state_flag("a", True),
            ValidationRule.event_emitted("b"),
        ]
        results = val_mod.validate_all(
            rules, {"a": True}, [{"type": "b"}])
        assert results["state_flag"] is True
        assert results["event_emitted"] is True

    def test_available_validators(self):
        # Ensure the extended validators from YC-031.0 are registered.
        from app.engines import validation_engine  # noqa: F401
        validators = val_mod.available_validators()
        assert "state_flag" in validators
        assert "exact_match" in validators
        assert len(validators) >= 10


# ===========================================================================
# Progress
# ===========================================================================
class TestProgress:
    def _scenario(self):
        return models.scenario_from_dict({
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
        p = prog_mod.calculate(self._scenario(), set())
        assert p.status == "not_started"
        assert p.ratio == 0.0

    def test_in_progress(self):
        p = prog_mod.calculate(self._scenario(), {1})
        assert p.status == "in_progress"
        assert p.current_objective_title == "B"

    def test_completed(self):
        p = prog_mod.calculate(self._scenario(), {1, 2})
        assert p.status == "completed"
        assert p.is_complete is True

    def test_objectives_summary(self):
        summary = prog_mod.objectives_summary(
            self._scenario(), {1})
        assert len(summary) == 3
        assert summary[0]["completed"] is True
        assert summary[2]["optional"] is True


# ===========================================================================
# Services (public API)
# ===========================================================================
class TestServices:
    def test_load_scenario_from_dict(self):
        s = load_scenario({"slug": "x", "title": "X"})
        assert isinstance(s, Scenario)
        assert s.slug == "x"

    def test_calculate_progress_via_service(self):
        s = load_scenario({
            "slug": "t",
            "objectives": [{"id": 1, "is_optional": False}],
        })
        p = calculate_progress(s, {1})
        assert p.status == "completed"

    def test_validate_submission_via_service(self):
        s = load_scenario({
            "slug": "t",
            "validation_rules": [
                {"validator_type": "state_flag",
                 "data": {"path": "x", "equals": True}},
            ],
        })
        # Manually set validation_rules since from_dict doesn't
        # parse them yet — use the Scenario directly.
        s.validation_rules = [
            ValidationRule.state_flag("x", True)]
        results = validate_submission(s, {"x": True})
        assert results["state_flag"] is True

    def test_generate_report_via_service(self):
        s = load_scenario({
            "slug": "t", "title": "T", "xp_reward": 100,
            "objectives": [{"id": 1, "is_optional": False,
                            "xp_reward": 20}],
        })
        p = calculate_progress(s, {1})
        report = generate_report(s, p)
        assert report["scenario"]["slug"] == "t"
        assert report["xp_earned"] == 120  # 100 lab + 20 objective


# ===========================================================================
# Backward compatibility with real ORM
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


class TestBackwardCompat:
    def test_load_forensics_lab(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="forensics-fundamentals").first()
            s = load_scenario(lab)
            assert s.slug == "forensics-fundamentals"
            assert s.difficulty == "Easy"
            assert s.xp_reward == 50
            assert len(s.objectives) == 5
            assert s.report_type == "forensics"
            # Every objective has a validation rule.
            for obj in s.objectives:
                assert obj.validation is not None

    def test_load_soc_lab(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="soc-analyst-fundamentals").first()
            s = load_scenario(lab)
            assert s.xp_reward == 150
            assert s.report_type == "incident"

    def test_load_assessment_lab(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="soc-blue-team-assessment").first()
            s = load_scenario(lab)
            assert s.xp_reward == 750
            assert s.report_type == "assessment"
            assert s.difficulty == "Expert"

    def test_progress_from_real_lab(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="forensics-fundamentals").first()
            s = load_scenario(lab)
            p = calculate_progress(s, set())
            assert p.status == "not_started"
            all_ids = {o.id for o in s.required_objectives}
            p2 = calculate_progress(s, all_ids)
            assert p2.status == "completed"

    def test_all_validators_available(self, app):
        validators = val_mod.available_validators()
        expected = ["exact_command", "regex_command",
                    "output_contains", "state_flag",
                    "event_emitted", "exact_match",
                    "multi_step", "ordered_tasks",
                    "score_threshold", "custom_hook"]
        for v in expected:
            assert v in validators, f"{v} missing"
