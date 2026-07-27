"""Tests for YC-030.7 — Blue Team Assessment."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0307-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_assess.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.simulators.soc import assessment_engine  # noqa: E402


class TestAssessmentScoring:
    def test_excellent_score(self):
        state = {
            "classifications": {
                "A1": "confirmed", "A2": "confirmed",
                "A3": "confirmed", "A4": "confirmed",
                "A5": "confirmed",
                "FP1": "false_positive", "FP2": "false_positive",
                "FP3": "false_positive",
            },
            "hunt_bookmarks": [{"ref": f"b{i}"} for i in range(5)],
            "hunt_searches": [{"results": 3}] * 5,
            "hunt_mitre_mapped": ["T1", "T2", "T3", "T4", "T5"],
            "ir_decisions": [{"correct": True, "points": 10}] * 5,
            "report": ("Executive summary of the enterprise breach. "
                       "Timeline shows phishing at 01:15, escalation "
                       "at 02:30. Evidence includes DNS tunneling "
                       "and HTTPS exfil. Root cause was credential "
                       "theft via phishing. Containment isolated "
                       "the segment. Recovery restored from backup. "
                       "Recommendations include MFA and MITRE mapping."),
            "hints_used": 0,
        }
        expected = {
            "classifications": {
                "A1": "confirmed", "A2": "confirmed",
                "A3": "confirmed", "A4": "confirmed",
                "A5": "confirmed",
                "FP1": "false_positive", "FP2": "false_positive",
                "FP3": "false_positive",
            },
        }
        score = assessment_engine.score_assessment(state, expected)
        assert score["grade"] == "Excellent"
        assert score["ratio"] >= 0.9

    def test_fail_on_empty(self):
        score = assessment_engine.score_assessment({}, {})
        assert score["grade"] == "Fail"
        assert score["total"] == 0

    def test_pass_threshold(self):
        state = {
            "classifications": {"A1": "confirmed", "A2": "confirmed",
                                "A3": "confirmed",
                                "FP1": "false_positive",
                                "FP2": "false_positive"},
            "hunt_bookmarks": [{"ref": "b1"}, {"ref": "b2"}],
            "hunt_searches": [{"results": 2}] * 3,
            "hunt_mitre_mapped": ["T1", "T2", "T3"],
            "ir_decisions": [{"correct": True, "points": 10}] * 3,
            "report": ("Executive summary. Timeline analysis. "
                       "Evidence review. Root cause identified. "
                       "Containment steps. Recovery plan. "
                       "Recommendations provided."),
            "hints_used": 0,
        }
        expected = {
            "classifications": {"A1": "confirmed", "A2": "confirmed",
                                "A3": "confirmed",
                                "FP1": "false_positive",
                                "FP2": "false_positive"},
        }
        score = assessment_engine.score_assessment(state, expected)
        assert score["grade"] in ("Pass", "Excellent")

    def test_hint_penalty(self):
        state = {"classifications": {"A1": "confirmed"},
                 "hunt_bookmarks": [], "hunt_searches": [],
                 "hunt_mitre_mapped": [], "ir_decisions": [],
                 "report": "", "hints_used": 10}
        score = assessment_engine.score_assessment(state,
                                                    {"classifications": {"A1": "confirmed"}})
        assert score["total"] == 0  # penalty exceeds points


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
        user = User(username="assess_tester", email="at@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "assess_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestAssessmentSeed:
    def test_lab_seeded(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="soc-blue-team-assessment").first()
            assert lab is not None
            assert lab.xp_reward == 750
            assert lab.difficulty == "Expert"
            assert len(lab.objectives) == 8

    def test_alerts_seeded(self, app):
        with app.app_context():
            from app.simulators.soc.models import SocAlert
            alerts = SocAlert.query.filter(
                SocAlert.alert_code.like("ASSESS%")).all()
            assert len(alerts) == 8
            real = [a for a in alerts
                    if a.expected_classification == "confirmed"]
            fp = [a for a in alerts
                  if a.expected_classification == "false_positive"]
            assert len(real) == 5
            assert len(fp) == 3

    def test_case_rich(self, app):
        with app.app_context():
            from app.labs.forensics.models import ForensicsCase
            case = ForensicsCase.query.filter_by(
                lab_slug="soc-assessment-enterprise-case").first()
            assert case is not None
            assert len(case.artifacts) >= 25
            assert len(case.suspects) == 4
            assert len(case.timeline) >= 12
            sources = {a.source_type for a in case.artifacts}
            assert sources >= {"event_log", "network_dns",
                               "network_https", "ioc_ip",
                               "ioc_domain", "ioc_hash"}

    def test_achievement(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            a = Achievement.query.filter_by(
                title="Blue Team Expert").first()
            assert a is not None
            assert a.bonus_xp == 300

    def test_certificate(self, app):
        with app.app_context():
            from app.certificates.models import Certificate
            c = Certificate.query.filter_by(
                slug="blue-team-analyst").first()
            assert c is not None
            assert c.certificate_type == "certification"

    def test_assessment_result_table(self, app):
        with app.app_context():
            from app.simulators.soc.models import AssessmentResult
            assert AssessmentResult.__tablename__ == "soc_assessment_results"

    def test_reseed_idempotent(self, app):
        with app.app_context():
            from app.labs.forensics.seed import seed_forensics_labs
            from app.labs.models import Lab
            before = Lab.query.filter_by(
                slug="soc-blue-team-assessment").count()
            seed_forensics_labs()
            after = Lab.query.filter_by(
                slug="soc-blue-team-assessment").count()
            assert before == after


class TestAssessmentHTTP:
    def test_state_endpoint(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-blue-team-assessment")
            r = client.get(
                "/labs/soc-blue-team-assessment/soc/state")
            assert r.status_code == 200
            data = r.get_json()
            assert data["active_alert"]["alert_code"] == "ASSESS-001"
            assert "assessment_score" in data

    def test_submit_assessment_action(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-blue-team-assessment")
            r = client.post(
                "/labs/soc-blue-team-assessment/action",
                json={"type": "submit_assessment",
                      "payload": {"report":
                          "Executive summary of investigation. "
                          "Timeline shows coordinated attack. "
                          "Evidence from DNS and HTTPS logs. "
                          "Root cause was credential phishing. "
                          "Containment isolated affected hosts. "
                          "Recovery restored from clean backups. "
                          "Recommendations include MFA enforcement."}})
            assert r.status_code == 200
            body = r.get_json()
            assert "assessment" in body.get("output", "").lower() \
                or "ASSESSMENT" in body.get("output", "")
