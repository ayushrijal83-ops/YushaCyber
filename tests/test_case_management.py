"""Tests for YC-030.3.5 — SOC Case Management System.

Covers:
  · models       — SocCase JSON helpers, status check.
  · case_manager — create, assign, note, link_evidence, link_alert,
                   escalate, close, dashboard_stats, case_timeline,
                   open_cases, recently_closed, idempotent create.
  · simulator    — open_case / assign_case / add_case_note /
                   link_case_evidence / escalate_case / close_case
                   actions emit the correct events.
  · HTTP         — /soc/state includes case_dashboard.
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc03035-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_cm.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402


# ===========================================================================
# Model unit tests (no app context needed for JSON helpers)
# ===========================================================================
class TestSocCaseModel:
    def test_json_helpers(self):
        from app.simulators.soc.models import SocCase
        c = SocCase(case_code="X-1", title="T")
        c.set_linked_alerts(["A-1", "A-2"])
        assert c.get_linked_alerts() == ["A-1", "A-2"]
        c.set_linked_evidence(["ev-1"])
        assert c.get_linked_evidence() == ["ev-1"]

    def test_is_open(self):
        from app.simulators.soc.models import SocCase
        for status in ("new", "in_progress", "escalated"):
            c = SocCase(case_code="X", title="T", status=status)
            assert c.is_open() is True
        for status in ("resolved", "closed"):
            c = SocCase(case_code="X", title="T", status=status)
            assert c.is_open() is False

    def test_case_statuses_constant(self):
        from app.simulators.soc.models import CASE_STATUSES
        assert "new" in CASE_STATUSES
        assert "closed" in CASE_STATUSES


# ===========================================================================
# Integration tests (throwaway SQLite app)
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
        user = User(username="cm_tester", email="cm@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "cm_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestCaseManagerEngine:
    def test_create_and_find(self, app):
        with app.app_context():
            from app.extensions import db
            from app.simulators.soc import case_manager
            c = case_manager.create_case(
                "CM-TEST-001", "Test Case", "high", ["A-1"])
            db.session.commit()
            assert c.case_code == "CM-TEST-001"
            assert c.status == "new"
            found = case_manager.find_by_code("CM-TEST-001")
            assert found is not None
            assert found.id == c.id

    def test_idempotent_create(self, app):
        with app.app_context():
            from app.simulators.soc import case_manager
            c1 = case_manager.find_by_code("CM-TEST-001")
            c2 = case_manager.create_case("CM-TEST-001", "Dup", "low")
            assert c2.id == c1.id

    def test_assign(self, app):
        with app.app_context():
            from app.extensions import db
            from app.simulators.soc import case_manager
            c = case_manager.find_by_code("CM-TEST-001")
            case_manager.assign_case(c, "analyst-a")
            db.session.commit()
            assert c.assigned_analyst == "analyst-a"
            assert c.status == "in_progress"

    def test_add_note(self, app):
        with app.app_context():
            from app.extensions import db
            from app.simulators.soc import case_manager
            c = case_manager.find_by_code("CM-TEST-001")
            case_manager.add_note(c, "analyst-a", "Note 1")
            case_manager.add_note(c, "analyst-a", "Note 2")
            db.session.commit()
            assert len(c.notes) == 2

    def test_link_alert_and_evidence(self, app):
        with app.app_context():
            from app.extensions import db
            from app.simulators.soc import case_manager
            c = case_manager.find_by_code("CM-TEST-001")
            case_manager.link_alert(c, "A-2")
            case_manager.link_evidence(c, "artifact-123")
            db.session.commit()
            assert "A-2" in c.get_linked_alerts()
            assert "artifact-123" in c.get_linked_evidence()
            # Idempotent
            case_manager.link_evidence(c, "artifact-123")
            assert c.get_linked_evidence().count("artifact-123") == 1

    def test_escalate(self, app):
        with app.app_context():
            from app.extensions import db
            from app.simulators.soc import case_manager
            c = case_manager.find_by_code("CM-TEST-001")
            case_manager.escalate_case(c)
            db.session.commit()
            assert c.status == "escalated"

    def test_dashboard_stats(self, app):
        with app.app_context():
            from app.simulators.soc import case_manager
            stats = case_manager.dashboard_stats()
            assert stats["open"] >= 1
            assert stats["total"] >= 1

    def test_open_cases_and_recently_closed(self, app):
        with app.app_context():
            from app.simulators.soc import case_manager
            open_list = case_manager.open_cases()
            assert any(c["case_code"] == "CM-TEST-001"
                       for c in open_list)
            closed_list = case_manager.recently_closed()
            assert not any(c["case_code"] == "CM-TEST-001"
                           for c in closed_list)

    def test_case_timeline(self, app):
        with app.app_context():
            from app.simulators.soc import case_manager
            c = case_manager.find_by_code("CM-TEST-001")
            tl = case_manager.case_timeline(c)
            assert len(tl) >= 3  # created + 2 notes

    def test_close_and_progress(self, app):
        with app.app_context():
            from app.extensions import db
            from app.simulators.soc import case_manager
            c = case_manager.find_by_code("CM-TEST-001")
            case_manager.close_case(c, "2026-07-25")
            db.session.commit()
            assert c.status == "closed"
            assert c.progress == 100
            assert c.closed_at == "2026-07-25"
            # Shows in recently_closed now
            closed_list = case_manager.recently_closed()
            assert any(c_["case_code"] == "CM-TEST-001"
                       for c_ in closed_list)


class TestCaseSimulatorActions:
    def _sim_state(self, app):
        from app.simulators.soc import services
        from app.simulators.soc.simulator import SOCSimulator
        sim = SOCSimulator()
        with app.app_context():
            workspace = services.workspace_context("ALERT-2026-0007")
            from app.labs.forensics.simulator import ForensicsSimulator
            fs = ForensicsSimulator().bootstrap(
                None, {"case": workspace.get("active_case") or {}})
            state = sim.new_state_envelope(
                forensics=fs, workspace=workspace,
                active_alert_code="ALERT-2026-0007",
                ticked=[], selected_playbook=None,
                root_cause="", report="",
                closure_checks={}, incident_closed=False,
                classifications={}, severity_assignments={},
                escalated=[], investigation_checks={},
                ir_decisions=[], ir_completed_phases=[],
                ir_score=None, active_case_code="")
        return sim, state

    def test_open_case_action(self, app):
        from app.labs.simulator_base import Action
        with app.app_context():
            sim, state = self._sim_state(app)
            r = sim.handle(state, Action("open_case", {
                "case_code": "CM-SIM-001",
                "title": "Sim test case",
                "severity": "high"}))
            assert r.new_state["active_case_code"] == "CM-SIM-001"
            assert any(e["type"] == "case_opened" for e in r.events)

    def test_assign_case_action(self, app):
        from app.labs.simulator_base import Action
        with app.app_context():
            sim, state = self._sim_state(app)
            sim.handle(state, Action("open_case", {
                "case_code": "CM-SIM-002", "title": "A",
                "severity": "medium"}))
            state["active_case_code"] = "CM-SIM-002"
            r = sim.handle(state, Action("assign_case", {
                "analyst": "Ayush"}))
            assert any(e["type"] == "case_assigned" for e in r.events)

    def test_add_case_note_action(self, app):
        from app.labs.simulator_base import Action
        with app.app_context():
            sim, state = self._sim_state(app)
            sim.handle(state, Action("open_case", {
                "case_code": "CM-SIM-003", "title": "B"}))
            state["active_case_code"] = "CM-SIM-003"
            r = sim.handle(state, Action("add_case_note", {
                "text": "Found lateral movement."}))
            assert any(e["type"] == "case_note_added" for e in r.events)

    def test_link_evidence_action(self, app):
        from app.labs.simulator_base import Action
        with app.app_context():
            sim, state = self._sim_state(app)
            sim.handle(state, Action("open_case", {
                "case_code": "CM-SIM-004", "title": "C"}))
            state["active_case_code"] = "CM-SIM-004"
            r = sim.handle(state, Action("link_case_evidence", {
                "evidence_ref": "dns-capture-pcap"}))
            assert any(e["type"] == "case_evidence_linked"
                       for e in r.events)

    def test_escalate_and_close(self, app):
        from app.labs.simulator_base import Action
        with app.app_context():
            sim, state = self._sim_state(app)
            sim.handle(state, Action("open_case", {
                "case_code": "CM-SIM-005", "title": "D"}))
            state["active_case_code"] = "CM-SIM-005"
            r = sim.handle(state, Action("escalate_case", {}))
            assert any(e["type"] == "case_escalated" for e in r.events)
            r = sim.handle(r.new_state, Action("close_case", {}))
            assert any(e["type"] == "case_closed" for e in r.events)


class TestCaseHTTP:
    def test_state_includes_case_dashboard(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-analyst-fundamentals")
            r = client.get(
                "/labs/soc-analyst-fundamentals/soc/state")
            assert r.status_code == 200
            data = r.get_json()
            assert "case_dashboard" in data
            assert "stats" in data["case_dashboard"]
            assert "open_cases" in data["case_dashboard"]
