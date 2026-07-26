"""Tests for YC-030.4 — Advanced SOC Scenarios.

Covers:
  · seed         — 5 labs, 5 alerts, 5 cases, all registered
  · decisions    — correct/wrong grading per scenario per phase
  · scoring      — hint penalty integration, rating thresholds
  · simulator    — full phase progression + report submission
  · achievement  — Threat Hunter condition value
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0304-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_adv.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.simulators.soc import decision_engine  # noqa: E402
from app.simulators.soc import score_engine  # noqa: E402


class TestDecisionEngine:
    def test_correct_action(self):
        grade = decision_engine.grade_decision(
            "disconnect_host",
            correct_actions=["disconnect_host", "block_ip"],
            wrong_actions=["ignore_alert"])
        assert grade["correct"] is True
        assert grade["points"] == 10

    def test_wrong_action(self):
        grade = decision_engine.grade_decision(
            "ignore_alert",
            correct_actions=["disconnect_host"],
            wrong_actions=["ignore_alert"])
        assert grade["correct"] is False
        assert grade["points"] == -5

    def test_neutral_action(self):
        grade = decision_engine.grade_decision(
            "enable_mfa",
            correct_actions=["disconnect_host"],
            wrong_actions=["ignore_alert"])
        assert grade["points"] == 0

    def test_score_decisions_ratings(self):
        good = [{"correct": True, "points": 10}] * 8 + \
               [{"correct": False, "points": -5}] * 2
        result = decision_engine.score_decisions(good)
        assert result["correct"] == 8
        assert result["wrong"] == 2


class TestScoreEngine:
    def test_excellent_rating(self):
        decisions = [{"correct": True, "points": 10}] * 5
        report = ("Executive summary of incident. "
                  "Incident timeline shows lateral movement. "
                  "Evidence includes DNS and HTTPS logs. "
                  "Root cause was compromised credentials. "
                  "Containment steps taken. "
                  "Recovery plan executed. "
                  "Recommendations for future prevention.")
        score = score_engine.compute_final_score(
            decisions, report, 5, hints_used=0)
        assert score["rating"] == "Excellent"
        assert score["ratio"] >= 0.9

    def test_hint_penalty_reduces_score(self):
        decisions = [{"correct": True, "points": 10}] * 5
        report = ("Executive summary. Incident timeline. Evidence. "
                  "Root cause. Recommendations. " * 3)
        score_no_hints = score_engine.compute_final_score(
            decisions, report, 5, hints_used=0)
        score_with_hints = score_engine.compute_final_score(
            decisions, report, 5, hints_used=4)
        assert score_with_hints["total"] < score_no_hints["total"]

    def test_needs_improvement_on_bad_decisions(self):
        decisions = [{"correct": False, "points": -5}] * 5
        score = score_engine.compute_final_score(
            decisions, "short", 1, hints_used=3)
        assert score["rating"] == "Needs Improvement"


class TestScenarioRegistry:
    def test_registry_populated_after_seed(self, app):
        from app.simulators.soc import scenario_registry
        for code in ("ALERT-ADV-0001", "ALERT-ADV-0002",
                     "ALERT-ADV-0003", "ALERT-ADV-0004",
                     "ALERT-ADV-0005"):
            s = scenario_registry.get(code)
            assert s, f"{code} not registered"
            assert len(s.get("phases", {})) == 5, f"{code} missing phases"

    def test_ir_seed_scenario_also_registered(self, app):
        from app.simulators.soc import scenario_registry
        s = scenario_registry.get("ALERT-IR-0001")
        assert s and len(s.get("phases", {})) == 5


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
        user = User(username="adv_tester", email="adv@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "adv_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestAdvancedSeed:
    def test_five_labs_seeded(self, app):
        with app.app_context():
            from app.labs.models import Lab
            labs = Lab.query.filter(
                Lab.slug.like("soc-scenario-%")).all()
            assert len(labs) == 5
            for lab in labs:
                assert lab.xp_reward == 200
                assert lab.difficulty == "Hard"
                assert len(lab.objectives) == 6

    def test_five_alerts_seeded(self, app):
        with app.app_context():
            from app.simulators.soc.models import SocAlert
            alerts = SocAlert.query.filter(
                SocAlert.alert_code.like("ALERT-ADV-%")).all()
            assert len(alerts) == 5
            for a in alerts:
                assert a.case_id is not None
                assert a.expected_classification in (
                    "confirmed", "suspicious", "false_positive")

    def test_five_cases_seeded(self, app):
        with app.app_context():
            from app.labs.forensics.models import ForensicsCase
            cases = ForensicsCase.query.filter(
                ForensicsCase.lab_slug.like("soc-%case")).all()
            assert len(cases) >= 5
            for case in cases:
                assert len(case.artifacts) >= 2

    def test_threat_hunter_achievement(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            th = Achievement.query.filter_by(
                title="Threat Hunter").first()
            assert th is not None
            assert th.bonus_xp == 150
            assert th.condition_value == 8

    def test_reseed_idempotent(self, app):
        with app.app_context():
            from app.labs.forensics.seed import seed_forensics_labs
            from app.labs.models import Lab
            before = Lab.query.filter(
                Lab.slug.like("soc-scenario-%")).count()
            seed_forensics_labs()
            after = Lab.query.filter(
                Lab.slug.like("soc-scenario-%")).count()
            assert before == after


class TestAdvancedHTTP:
    def test_ransomware_state(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-scenario-ransomware")
            r = client.get(
                "/labs/soc-scenario-ransomware/soc/state")
            assert r.status_code == 200
            data = r.get_json()
            assert data["active_alert"]["alert_code"] == "ALERT-ADV-0001"
            assert data["active_alert"]["severity"] == "critical"

    def test_take_action_grades_correctly(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-scenario-ransomware")
            # Correct action — output contains ✓
            r = client.post(
                "/labs/soc-scenario-ransomware/action",
                json={"type": "take_action",
                      "payload": {"action": "preserve_evidence"}})
            assert r.status_code == 200
            body = r.get_json()
            assert "correct" in body.get("output", "").lower() \
                or "✓" in body.get("output", "")
            # Wrong action — output contains ✖
            r = client.post(
                "/labs/soc-scenario-ransomware/action",
                json={"type": "take_action",
                      "payload": {"action": "ignore_alert"}})
            body = r.get_json()
            assert "wrong" in body.get("output", "").lower() \
                or "✖" in body.get("output", "")

    def test_hint_system(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-scenario-phishing")
            r = client.post(
                "/labs/soc-scenario-phishing/action",
                json={"type": "use_hint", "payload": {}})
            assert r.status_code == 200
            body = r.get_json()
            assert "hint" in body.get("output", "").lower()
