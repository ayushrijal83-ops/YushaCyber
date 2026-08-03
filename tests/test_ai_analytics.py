"""Tests for YC-032.5 — AI Analytics & Instructor Dashboard."""

from __future__ import annotations

import json
import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0325-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_ai_analytics.db"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["AI_PROVIDER"] = "mock"

import pytest  # noqa: E402

from app.core.ai.analytics import (  # noqa: E402
    dashboard_dict,
    dashboard_metrics,
    export_data,
    get_charts,
    get_report,
    refresh,
)
from app.core.ai.analytics.models import (  # noqa: E402
    AIHealthMetrics,
    AIUsageMetrics,
    DashboardData,
)


# ===========================================================================
# Models (pure unit tests)
# ===========================================================================
class TestModels:
    def test_dashboard_to_dict(self):
        d = DashboardData()
        result = d.to_dict()
        assert "ai_usage" in result
        assert "students" in result
        assert "hints" in result
        assert "labs" in result
        assert "health" in result

    def test_ai_usage_to_dict(self):
        u = AIUsageMetrics(total_conversations=100, messages_today=5)
        d = u.to_dict()
        assert d["total_conversations"] == 100

    def test_health_to_dict(self):
        h = AIHealthMetrics(provider="openai", model="gpt-4o", status="ok")
        assert h.to_dict()["status"] == "ok"


# ===========================================================================
# Engine (needs app context)
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
def admin(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="ai_admin", email="aia@t.io",
                     is_admin=True)
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "ai_admin"


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="ai_student", email="ais@t.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "ai_student"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestEngine:
    def test_dashboard_metrics(self, app):
        with app.app_context():
            refresh()
            d = dashboard_metrics()
            assert isinstance(d, DashboardData)
            assert d.health.status in ("ok", "disabled", "error")

    def test_dashboard_dict(self, app):
        with app.app_context():
            d = dashboard_dict()
            assert "ai_usage" in d
            assert "students" in d

    def test_caching(self, app):
        with app.app_context():
            refresh()
            d1 = dashboard_dict()
            d2 = dashboard_dict()  # should be cached
            assert d1["health"]["provider"] == d2["health"]["provider"]


class TestReports:
    def test_daily_report(self, app):
        with app.app_context():
            r = get_report("daily")
            assert r["type"] == "daily"
            assert "generated_at" in r

    def test_weekly_report(self, app):
        with app.app_context():
            r = get_report("weekly")
            assert r["type"] == "weekly"
            assert "hint_success_rate" in r

    def test_monthly_report(self, app):
        with app.app_context():
            r = get_report("monthly")
            assert r["type"] == "monthly"
            assert "summary" in r


class TestCharts:
    def test_all_charts(self, app):
        with app.app_context():
            charts = get_charts()
            assert len(charts) == 4
            types = [c["chart"] for c in charts]
            assert "ai_conversations" in types
            assert "hint_levels" in types


class TestExport:
    def test_export_json(self, app):
        with app.app_context():
            data = export_data("all", "json")
            parsed = json.loads(data)
            assert "ai_usage" in parsed

    def test_export_csv(self, app):
        with app.app_context():
            data = export_data("students", "csv")
            assert "total_active" in data


class TestHTTP:
    def test_analytics_admin_only(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.get("/api/ai/admin/analytics")
            assert r.status_code == 403

    def test_analytics_endpoint(self, app, admin):
        with app.test_client() as client:
            _login(client, admin)
            r = client.get("/api/ai/admin/analytics")
            assert r.status_code == 200
            assert "ai_usage" in r.get_json()

    def test_report_endpoint(self, app, admin):
        with app.test_client() as client:
            _login(client, admin)
            r = client.get("/api/ai/admin/report?period=daily")
            assert r.status_code == 200
            assert r.get_json()["type"] == "daily"

    def test_export_endpoint(self, app, admin):
        with app.test_client() as client:
            _login(client, admin)
            r = client.get("/api/ai/admin/export?dataset=all&format=json")
            assert r.status_code == 200

    def test_charts_endpoint(self, app, admin):
        with app.test_client() as client:
            _login(client, admin)
            r = client.get("/api/ai/admin/charts")
            assert r.status_code == 200
            assert "charts" in r.get_json()

    def test_dashboard_page(self, app, admin):
        with app.test_client() as client:
            _login(client, admin)
            r = client.get("/admin/ai")
            assert r.status_code == 200
            assert b"CyberMentor" in r.data or b"AI" in r.data
