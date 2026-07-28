"""Tests for YC-031.2 — Universal Assessment Engine.

Covers every submodule: types, grading, engine, certificate,
analytics, services. Plus backward-compatibility checks.
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0312-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_assess_eng.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.core.assessment import (  # noqa: E402
    AssessmentResult,
    CertificateType,
    GradeThreshold,
    GradingInput,
    PASS_FAIL_SCALE,
    XPConfig,
    analytics_summary,
    assessment_summary,
    calculate_grade,
    calculate_xp,
    complete_assessment,
    create_assessment,
    grade_from_ratio,
)


# ===========================================================================
# Types + grade scales
# ===========================================================================
class TestTypes:
    def test_grade_from_ratio_default(self):
        assert grade_from_ratio(0.98) == "A+"
        assert grade_from_ratio(0.94) == "A"
        assert grade_from_ratio(0.88) == "B"
        assert grade_from_ratio(0.77) == "C"
        assert grade_from_ratio(0.66) == "D"
        assert grade_from_ratio(0.40) == "F"

    def test_grade_from_ratio_pass_fail(self):
        assert grade_from_ratio(0.95, PASS_FAIL_SCALE) == "Excellent"
        assert grade_from_ratio(0.70, PASS_FAIL_SCALE) == "Pass"
        assert grade_from_ratio(0.45, PASS_FAIL_SCALE) == "Needs Improvement"
        assert grade_from_ratio(0.20, PASS_FAIL_SCALE) == "Fail"

    def test_custom_scale(self):
        custom = [
            GradeThreshold("Gold", 0.90),
            GradeThreshold("Silver", 0.70),
            GradeThreshold("Bronze", 0.0),
        ]
        assert grade_from_ratio(0.95, custom) == "Gold"
        assert grade_from_ratio(0.75, custom) == "Silver"
        assert grade_from_ratio(0.50, custom) == "Bronze"

    def test_certificate_type_enum(self):
        assert CertificateType.COMPLETION.value == "completion"
        assert CertificateType.ASSESSMENT.value == "assessment"

    def test_assessment_result_ratio(self):
        r = AssessmentResult(final_score=80, max_score=100)
        assert r.ratio == 0.8
        assert r.to_dict()["ratio"] == 0.8

    def test_assessment_result_zero_max(self):
        r = AssessmentResult(final_score=0, max_score=0)
        assert r.ratio == 0.0


# ===========================================================================
# XP Config
# ===========================================================================
class TestXPConfig:
    def test_base_calculation(self):
        cfg = XPConfig(base_xp=200, difficulty_multiplier=1.5)
        result = cfg.calculate(score_ratio=0.8)
        assert result["base"] == 300
        assert result["total"] == 300

    def test_perfect_bonus(self):
        cfg = XPConfig(base_xp=100, perfect_bonus=50)
        result = cfg.calculate(score_ratio=1.0)
        assert result["perfect_bonus"] == 50
        assert result["total"] == 150

    def test_no_perfect_bonus_below_100(self):
        cfg = XPConfig(base_xp=100, perfect_bonus=50)
        result = cfg.calculate(score_ratio=0.99)
        assert result["perfect_bonus"] == 0

    def test_speed_bonus(self):
        cfg = XPConfig(base_xp=100, speed_bonus_max=25,
                       speed_threshold_seconds=300)
        result = cfg.calculate(score_ratio=0.8, time_seconds=200)
        assert result["speed_bonus"] == 25

    def test_no_speed_bonus_if_slow(self):
        cfg = XPConfig(base_xp=100, speed_bonus_max=25,
                       speed_threshold_seconds=300)
        result = cfg.calculate(score_ratio=0.8, time_seconds=400)
        assert result["speed_bonus"] == 0

    def test_hint_penalty(self):
        cfg = XPConfig(base_xp=100, hint_penalty_per=10)
        result = cfg.calculate(score_ratio=0.8, hints_used=3)
        assert result["hint_penalty"] == 30
        assert result["total"] == 70

    def test_attempt_penalty(self):
        cfg = XPConfig(base_xp=100, attempt_penalty_per=15)
        result = cfg.calculate(score_ratio=0.8, attempts=3)
        assert result["attempt_penalty"] == 30
        assert result["total"] == 70

    def test_floor_at_zero(self):
        cfg = XPConfig(base_xp=10, hint_penalty_per=100)
        result = cfg.calculate(score_ratio=0.5, hints_used=5)
        assert result["total"] == 0


# ===========================================================================
# Grading
# ===========================================================================
class TestGrading:
    def test_calculate_grade_simple(self):
        inp = GradingInput(correct=9, total=10,
                           completed_objectives=5, total_objectives=5)
        result = calculate_grade(inp)
        assert result["grade"] != ""
        assert result["final_ratio"] >= 0

    def test_hint_penalty_lowers_score(self):
        no_hints = calculate_grade(
            GradingInput(correct=9, total=10,
                         completed_objectives=5, total_objectives=5))
        with_hints = calculate_grade(
            GradingInput(correct=9, total=10,
                         completed_objectives=5, total_objectives=5,
                         hints_used=5, hint_penalty_pct=0.05))
        assert with_hints["final_ratio"] <= no_hints["final_ratio"]


# ===========================================================================
# Services
# ===========================================================================
class TestServices:
    def test_create_assessment(self):
        a = create_assessment(scenario_id=1, student_id=1)
        assert a.scenario_id == 1
        assert a.student_id == 1
        assert a.passed is False

    def test_complete_assessment(self):
        a = create_assessment(scenario_id=1, student_id=1)
        completed = complete_assessment(a, raw_score=85, max_score=100)
        assert completed.passed is True
        assert completed.grade != ""
        assert completed.final_score > 0

    def test_assessment_summary(self):
        a = create_assessment(scenario_id=1, student_id=1)
        a = complete_assessment(a, raw_score=80, max_score=100)
        summary = assessment_summary(a)
        assert "grade" in summary
        assert "passed" in summary

    def test_calculate_xp_via_config(self):
        cfg = XPConfig(base_xp=200, difficulty_multiplier=1.5,
                       hint_penalty_per=5)
        xp = calculate_xp(cfg, score_ratio=0.9, hints_used=1)
        assert xp["total"] > 0
        assert xp["base"] == 300

    def test_analytics_summary(self):
        results = [
            AssessmentResult(final_score=80, max_score=100,
                             time_taken_seconds=300, xp_earned=200,
                             passed=True, grade="B"),
            AssessmentResult(final_score=60, max_score=100,
                             time_taken_seconds=600, xp_earned=150,
                             passed=False, grade="D"),
        ]
        stats = analytics_summary(results)
        assert stats["average_score"] == 70.0
        assert stats["highest_score"] == 80
        assert stats["lowest_score"] == 60
        assert stats["total_xp_earned"] == 350
        assert stats["pass_rate"] == 0.5

    def test_analytics_empty(self):
        stats = analytics_summary([])
        assert stats["average_score"] == 0.0
        assert stats["total_xp_earned"] == 0
        assert stats["count"] == 0


# ===========================================================================
# Backward compatibility
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
    def test_existing_award_xp(self, app):
        with app.app_context():
            from app.auth.models import User
            from app.extensions import db
            user = User(username="xp_test_312", email="xp312@t.io")
            user.set_password("Str0ngPass!")
            db.session.add(user)
            db.session.commit()
            from app.dashboard.services import award_xp
            award_xp(user, 50)
            assert user.xp >= 50

    def test_existing_certificate_service(self, app):
        with app.app_context():
            from app.certificates.models import Certificate
            assert Certificate.query.first() is not None

    def test_existing_achievement_service(self, app):
        with app.app_context():
            from app.achievement.services import check_and_unlock_achievements
            from app.auth.models import User
            user = User.query.filter_by(username="xp_test_312").first()
            result = check_and_unlock_achievements(user)
            assert "unlocked" in result

    def test_core_wraps_without_conflict(self, app):
        with app.app_context():
            a = create_assessment(scenario_id=1, student_id=1)
            completed = complete_assessment(a, raw_score=90, max_score=100)
            assert completed.grade in ("A+", "A", "B")
            assert completed.passed is True
