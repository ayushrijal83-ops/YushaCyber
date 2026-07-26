"""Tests for YC-030.5 — SOC Capstone: Operation Black Phoenix.

Covers:
  · seed          — lab, alert, case (19 artifacts, 3 suspects),
                    achievement, certificate, registry, idempotent
  · HTTP          — state endpoint returns capstone data
  · architecture  — certificate requires all 9 SOC lab slugs
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0305-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_cap.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402


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
        seed_forensics_labs()  # idempotency
    yield application


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="cap_tester", email="cap@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "cap_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestCapSeed:
    def test_lab_seeded(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="soc-capstone-black-phoenix").first()
            assert lab is not None
            assert lab.difficulty == "Expert"
            assert lab.xp_reward == 500
            assert len(lab.objectives) == 9

    def test_alert_linked_to_case(self, app):
        with app.app_context():
            from app.simulators.soc.models import SocAlert
            alert = SocAlert.query.filter_by(
                alert_code="ALERT-PHOENIX-001").first()
            assert alert is not None
            assert alert.severity == "critical"
            assert alert.case_id is not None
            assert alert.expected_classification == "confirmed"

    def test_case_rich_content(self, app):
        with app.app_context():
            from app.labs.forensics.models import ForensicsCase
            case = ForensicsCase.query.filter_by(
                lab_slug="soc-capstone-phoenix-case").first()
            assert case is not None
            assert case.mode == "advanced"
            assert len(case.artifacts) >= 15
            assert len(case.suspects) == 3
            assert len(case.evidence) == 3
            assert len(case.timeline) >= 10
            # Key artifacts across multiple source types.
            sources = {a.source_type for a in case.artifacts}
            assert sources >= {"event_log", "network_dns",
                               "network_https", "browser_history",
                               "login_history", "downloads"}

    def test_checklist_seeded(self, app):
        with app.app_context():
            from app.labs.forensics.models import ForensicsCase
            from app.simulators.soc.models import SocChecklistItem
            case = ForensicsCase.query.filter_by(
                lab_slug="soc-capstone-phoenix-case").first()
            items = SocChecklistItem.query.filter_by(
                case_id=case.id).all()
            assert len(items) == 9
            required = [i for i in items if i.is_required]
            assert len(required) == 9

    def test_achievement_seeded(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            a = Achievement.query.filter_by(
                title="SOC Master").first()
            assert a is not None
            assert a.bonus_xp == 250
            assert a.condition_value == 9

    def test_certificate_seeded(self, app):
        with app.app_context():
            from app.certificates.models import Certificate
            cert = Certificate.query.filter_by(
                slug="soc-analyst-completion").first()
            assert cert is not None
            assert cert.certificate_type == "track"
            # Must require all 9 SOC lab slugs.
            slugs = (cert.required_labs or "").split(",")
            assert len(slugs) == 9
            assert "soc-capstone-black-phoenix" in slugs
            assert "soc-analyst-fundamentals" in slugs

    def test_scenario_registered(self, app):
        with app.app_context():
            from app.simulators.soc import scenario_registry
            reg = scenario_registry.get("ALERT-PHOENIX-001")
            assert reg is not None
            assert len(reg.get("phases", {})) == 5

    def test_reseed_idempotent(self, app):
        with app.app_context():
            from app.labs.forensics.seed import seed_forensics_labs
            from app.labs.models import Lab
            before = Lab.query.filter_by(
                slug="soc-capstone-black-phoenix").count()
            seed_forensics_labs()
            after = Lab.query.filter_by(
                slug="soc-capstone-black-phoenix").count()
            assert before == after


class TestCapHTTP:
    def test_state_returns_capstone(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-capstone-black-phoenix")
            r = client.get(
                "/labs/soc-capstone-black-phoenix/soc/state")
            assert r.status_code == 200
            data = r.get_json()
            assert data["active_alert"] is not None
            assert data["active_alert"]["alert_code"] \
                == "ALERT-PHOENIX-001"
            assert data["active_alert"]["severity"] == "critical"
            # Forensics view should have rich artifact data.
            view = data.get("view") or {}
            assert len(view.get("suspects", [])) == 3
            assert len(view.get("unified_timeline", [])) >= 10

    def test_lab_detail_renders(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.get("/labs/soc-capstone-black-phoenix",
                           follow_redirects=True)
            assert r.status_code == 200
