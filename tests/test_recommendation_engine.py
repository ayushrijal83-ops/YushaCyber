"""Tests for YC-032.4 — Personalized Learning Recommendations."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0324-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_recs.db"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["AI_PROVIDER"] = "mock"

import pytest  # noqa: E402

from app.core.ai.recommendations import (  # noqa: E402
    DailyPlan,
    Recommendation,
    SkillProfile,
    WeeklyPlan,
    accept_recommendation,
    get_daily_plan,
    get_recommendations,
    get_skill_profile,
    get_weekly_plan,
    recommendation_history,
)
from app.core.ai.recommendations.history import (  # noqa: E402
    clear as clear_history,
)


# ===========================================================================
# Models (pure unit tests)
# ===========================================================================
class TestModels:
    def test_recommendation_to_dict(self):
        r = Recommendation(title="Learn Nmap", slug="nmap-basics",
                           priority=80, reason="Foundation skill")
        d = r.to_dict()
        assert d["title"] == "Learn Nmap"
        assert d["priority"] == 80

    def test_skill_profile(self):
        p = SkillProfile(strongest_topics=["SOC"],
                         weakest_topics=["Networking"],
                         recommended_difficulty="Hard")
        d = p.to_dict()
        assert d["recommended_difficulty"] == "Hard"

    def test_daily_plan(self):
        dp = DailyPlan(
            recommendations=[
                Recommendation(title="A"), Recommendation(title="B")],
            review_topic="DNS", challenge="CTF")
        d = dp.to_dict()
        assert len(d["recommendations"]) == 2
        assert d["review_topic"] == "DNS"

    def test_weekly_plan(self):
        wp = WeeklyPlan(
            days={"Monday": [Recommendation(title="Lab A")]},
            total_estimated_minutes=120)
        d = wp.to_dict()
        assert "Monday" in d["days"]
        assert len(d["days"]["Monday"]) == 1


# ===========================================================================
# Integration (needs app context)
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


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="rec_tester", email="rec@t.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "rec_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestIntegration:
    def test_get_recommendations(self, app, student):
        with app.app_context():
            from app.auth.models import User
            u = User.query.filter_by(username="rec_tester").first()
            recs = get_recommendations(u, limit=5)
            assert isinstance(recs, list)
            assert all(isinstance(r, Recommendation) for r in recs)
            if recs:
                assert recs[0].title != ""

    def test_get_skill_profile(self, app, student):
        with app.app_context():
            from app.auth.models import User
            u = User.query.filter_by(username="rec_tester").first()
            p = get_skill_profile(u)
            assert isinstance(p, SkillProfile)
            assert p.recommended_difficulty in (
                "Easy", "Medium", "Hard", "Expert")

    def test_get_daily_plan(self, app, student):
        with app.app_context():
            from app.auth.models import User
            u = User.query.filter_by(username="rec_tester").first()
            dp = get_daily_plan(u)
            assert isinstance(dp, DailyPlan)

    def test_get_weekly_plan(self, app, student):
        with app.app_context():
            from app.auth.models import User
            u = User.query.filter_by(username="rec_tester").first()
            wp = get_weekly_plan(u)
            assert isinstance(wp, WeeklyPlan)
            assert "Monday" in wp.days

    def test_accept_and_history(self, app, student):
        with app.app_context():
            from app.auth.models import User
            u = User.query.filter_by(username="rec_tester").first()
            clear_history(u.id)
            accept_recommendation(u.id, "nmap-basics")
            h = recommendation_history(u.id)
            assert len(h) >= 1
            clear_history(u.id)


class TestHTTP:
    def test_recommendations_endpoint(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.get("/api/ai/recommendations")
            assert r.status_code == 200
            body = r.get_json()
            assert "recommendations" in body

    def test_skill_profile_endpoint(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.get("/api/ai/skill-profile")
            assert r.status_code == 200
            body = r.get_json()
            assert "recommended_difficulty" in body

    def test_requires_login(self, app):
        with app.test_client() as client:
            r = client.get("/api/ai/recommendations")
            assert r.status_code in (302, 401)
