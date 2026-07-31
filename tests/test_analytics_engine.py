"""Tests for YC-031.5 — Universal Analytics Engine."""

from __future__ import annotations

import json
import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0315-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_analytics.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.core.analytics import (  # noqa: E402
    AdminDashboard,
    AssessmentMetrics,
    EngagementMetrics,
    StudentMetrics,
    TrackMetrics,
    admin_summary,
    assessment_summary,
    engagement_summary,
    export_analytics_csv,
    export_analytics_json,
    insights_for_student,
    insights_for_track,
    student_summary,
    track_summary,
)
from app.core.analytics.metrics import (  # noqa: E402
    average,
    completion_rate,
    difficulty_distribution,
    grade_distribution,
    grade_from_scores,
    pass_fail_rates,
    score_distribution,
)


# ===========================================================================
# Pure metrics
# ===========================================================================
class TestMetrics:
    def test_completion_rate(self):
        assert completion_rate(3, 10) == 0.3
        assert completion_rate(0, 0) == 0.0
        assert completion_rate(10, 10) == 1.0

    def test_average(self):
        assert average([80, 90, 100]) == 90.0
        assert average([]) == 0.0

    def test_grade_from_scores(self):
        assert grade_from_scores([95, 93]) == "A"
        assert grade_from_scores([70, 60]) == "D"
        assert grade_from_scores([]) == ""

    def test_grade_distribution(self):
        d = grade_distribution(["A", "B", "A", "C", "A"])
        assert d["A"] == 3
        assert d["B"] == 1

    def test_score_distribution(self):
        d = score_distribution([10, 30, 50, 70, 90])
        assert sum(d.values()) >= 5

    def test_difficulty_distribution(self):
        d = difficulty_distribution(["Easy", "Hard", "Easy", "Expert"])
        assert d["Easy"] == 2
        assert d["Expert"] == 1

    def test_pass_fail_rates(self):
        pr, fr = pass_fail_rates(7, 10)
        assert pr == 0.7
        assert fr == 0.3
        pr0, fr0 = pass_fail_rates(0, 0)
        assert pr0 == 0.0


# ===========================================================================
# Aggregation / summaries
# ===========================================================================
class TestSummaries:
    def test_student_summary(self):
        s = student_summary({
            "student_id": 1, "username": "Ayush",
            "total_xp": 5000, "level": 25,
            "completed_labs": 30, "total_labs": 50,
            "certificates_earned": 2, "achievements_earned": 8,
            "scores": [85, 90, 75], "times": [300, 600],
        })
        assert isinstance(s, StudentMetrics)
        assert s.completion_rate == 0.6
        assert s.average_score == 83.3
        assert s.average_grade == "C"
        assert s.average_time_seconds == 450

    def test_track_summary(self):
        t = track_summary({
            "track_slug": "soc", "track_name": "SOC Analyst",
            "total_labs": 10, "completed": 8,
            "difficulties": ["Easy", "Medium", "Hard", "Hard"],
            "times": [600, 900],
        })
        assert isinstance(t, TrackMetrics)
        assert t.completion_pct == 0.8
        assert t.difficulty_distribution["Hard"] == 2

    def test_assessment_summary(self):
        a = assessment_summary({
            "assessment_slug": "blue-team",
            "total_attempts": 20, "passed": 14,
            "scores": [80, 60, 90, 70],
            "grades": ["B", "D", "A", "C"],
            "attempts_list": [1, 2, 1],
            "times": [3600, 5400],
        })
        assert isinstance(a, AssessmentMetrics)
        assert a.pass_rate == 0.7
        assert a.fail_rate == 0.3
        assert a.grade_distribution["B"] == 1

    def test_engagement_summary(self):
        e = engagement_summary({
            "daily_active": 15, "weekly_active": 80,
            "monthly_active": 200,
            "streaks": [5, 10, 3], "study_minutes": [30, 60],
        })
        assert isinstance(e, EngagementMetrics)
        assert e.daily_active == 15
        assert e.average_streak == 6.0

    def test_admin_summary_from_dict(self):
        a = admin_summary({
            "total_students": 100, "total_xp_earned": 50000,
            "certificates_issued": 20,
            "achievements_unlocked": 150,
            "labs_completed": 800,
            "top_students": [{"username": "Ayush", "xp": 5000}],
        })
        assert isinstance(a, AdminDashboard)
        assert a.total_students == 100
        assert len(a.top_students) == 1


# ===========================================================================
# Insights
# ===========================================================================
class TestInsights:
    def test_low_completion_insight(self):
        s = StudentMetrics(username="Test", completion_rate=0.2)
        insights = insights_for_student(s)
        assert any("low completion" in i.message for i in insights)
        assert any(i.severity == "warning" for i in insights)

    def test_excellent_completion(self):
        s = StudentMetrics(username="Star", completion_rate=0.95)
        insights = insights_for_student(s)
        assert any("excellent" in i.message for i in insights)

    def test_streak_insight(self):
        s = StudentMetrics(username="Streak", current_streak=10)
        insights = insights_for_student(s)
        assert any("streak" in i.message for i in insights)

    def test_no_insights_for_average(self):
        s = StudentMetrics(username="Average", completion_rate=0.5,
                           hints_used=5, current_streak=3,
                           average_time_seconds=600)
        insights = insights_for_student(s)
        assert len(insights) == 0

    def test_track_insight(self):
        insights = insights_for_track({
            "track_name": "Networking", "completion_pct": 0.1})
        assert len(insights) == 1
        assert "Networking" in insights[0].message


# ===========================================================================
# Export
# ===========================================================================
class TestExport:
    def test_export_json(self):
        s = StudentMetrics(username="Test", total_xp=1000)
        j = export_analytics_json(s)
        data = json.loads(j)
        assert data["username"] == "Test"
        assert data["total_xp"] == 1000

    def test_export_csv(self):
        rows = [
            {"name": "A", "score": 90},
            {"name": "B", "score": 80},
        ]
        csv_str = export_analytics_csv(rows)
        assert "name,score" in csv_str
        assert "A,90" in csv_str

    def test_export_csv_empty(self):
        assert export_analytics_csv([]) == ""


# ===========================================================================
# Backward compatibility with ORM
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
    def test_student_summary_from_user(self, app):
        with app.app_context():
            from app.auth.models import User
            from app.extensions import db
            from app.core.analytics import student_summary_from_user
            user = User(username="analytics_test", email="an@t.io")
            user.set_password("Str0ngPass!")
            db.session.add(user)
            db.session.commit()
            s = student_summary_from_user(user)
            assert isinstance(s, StudentMetrics)
            assert s.username == "analytics_test"
            assert s.total_labs > 0

    def test_admin_summary_from_db(self, app):
        with app.app_context():
            a = admin_summary()
            assert isinstance(a, AdminDashboard)
            assert a.total_students >= 1

    def test_existing_dashboard_still_works(self, app):
        with app.app_context():
            from app.dashboard.services import _get_stats
            from app.auth.models import User
            user = User.query.first()
            stats = _get_stats(user)
            assert isinstance(stats, list)
