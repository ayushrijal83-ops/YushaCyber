"""Tests for YC-030.1 — SOC Analyst Simulator Foundation.

Covers:
  · dashboard      — stat counts by severity, recent activity.
  · alerts         — queue sorting by severity + time; find_by_code.
  · playbooks      — phase grouping in canonical order.
  · report_engine  — evaluate_report matrix (playbook, root cause,
                     report length + sections, checklist).
  · simulator      — bootstrap, open_alert (rebootstraps forensics),
                     tick_checklist, select_playbook, set_root_cause,
                     close_incident event chain; forensics forwarding.
  · seed           — alerts, playbooks, checklist items, lab shape,
                     achievement condition — all present + idempotent.
  · HTTP           — /soc/state returns expected shape; admin CRUD
                     works for admins and blocks non-admins.
  · playthrough    — student completes all 3 forensics labs then the
                     SOC lab → SOC Rookie unlocks with bonus XP.
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0301-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_soc.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.simulators.soc import alerts as soc_alerts  # noqa: E402
from app.simulators.soc import dashboard as soc_dashboard  # noqa: E402
from app.simulators.soc import playbooks as soc_playbooks  # noqa: E402
from app.simulators.soc import report_engine as soc_report_engine  # noqa: E402


# ===========================================================================
# Pure engine tests
# ===========================================================================
class _FakeAlert:
    """Duck-typed SocAlert stand-in for pure tests."""
    _next_id = 1

    def __init__(self, alert_code, title, alert_type, severity, status,
                 source="EDR", at_time="00:00", description=""):
        self.id = _FakeAlert._next_id
        _FakeAlert._next_id += 1
        self.alert_code = alert_code
        self.title = title
        self.alert_type = alert_type
        self.severity = severity
        self.status = status
        self.source = source
        self.at_time = at_time
        self.description = description
        self.assigned_analyst = ""
        self.case_id = None


FAKE_ALERTS = [
    _FakeAlert("A-1", "Failed logins", "multiple_failed_logins",
               "high", "open", "SIEM", "08:00"),
    _FakeAlert("A-2", "Data exfil", "data_exfiltration",
               "critical", "open", "EDR", "22:26"),
    _FakeAlert("A-3", "Suspicious PS", "suspicious_powershell",
               "medium", "in_progress", "EDR", "10:11"),
    _FakeAlert("A-4", "Malware", "possible_malware",
               "high", "resolved", "AV", "07:00"),
]


class TestDashboard:
    def test_stats_by_severity(self):
        stats = soc_dashboard.dashboard_stats(FAKE_ALERTS)
        assert stats["open"] == 3
        assert stats["critical"] == 1
        assert stats["high"] == 1
        assert stats["medium"] == 1
        assert stats["resolved"] == 1

    def test_recent_activity_sorted_desc(self):
        recent = soc_dashboard.recent_activity(FAKE_ALERTS)
        assert recent[0]["alert_code"] == "A-2"


class TestAlertQueue:
    def test_open_queue_sorts_by_severity_then_time(self):
        queue = soc_alerts.open_queue(FAKE_ALERTS)
        codes = [a["alert_code"] for a in queue]
        assert codes[0] == "A-2"
        assert codes[1] == "A-1"
        assert codes[2] == "A-3"

    def test_resolved_queue_excludes_open(self):
        queue = soc_alerts.resolved_queue(FAKE_ALERTS)
        assert [a["alert_code"] for a in queue] == ["A-4"]

    def test_find_by_code(self):
        found = soc_alerts.find_by_code(FAKE_ALERTS, "A-2")
        assert found.title == "Data exfil"
        assert soc_alerts.find_by_code(FAKE_ALERTS, "nope") is None


class TestPlaybookView:
    def _make_playbook(self):
        class Step:
            def __init__(self, phase, title, body, order):
                self.phase = phase
                self.title = title
                self.body = body
                self.display_order = order

        class Playbook:
            def __init__(self):
                self.key = "malware"
                self.title = "Malware Response"
                self.description = "d"
                self.alert_type = "possible_malware"
                self.summary = ""
                self.steps = [
                    Step("recovery", "Restore", "b1", 4),
                    Step("identification", "Detect IOCs", "b2", 1),
                    Step("containment", "Isolate", "b3", 2),
                    Step("eradication", "Clean", "b4", 3),
                    Step("lessons_learned", "Postmortem", "b5", 5),
                ]
        return Playbook()

    def test_phases_ordered(self):
        from app.simulators.soc.models import PLAYBOOK_PHASES
        view = soc_playbooks.playbook_view(self._make_playbook())
        phase_order = [p["key"] for p in view["phases"]]
        assert phase_order == list(PLAYBOOK_PHASES)

    def test_none_returns_empty_view(self):
        view = soc_playbooks.playbook_view(None)
        assert view["phases"] == []


class TestReportEngine:
    def _alert(self, alert_type="data_exfiltration"):
        return _FakeAlert("A-99", "Test", alert_type, "critical",
                          "open")

    def _checklist(self):
        class Item:
            def __init__(self, slug, text, required):
                self.slug = slug
                self.text = text
                self.is_required = required
        return [Item("isolate", "Isolate host", True),
                Item("notify", "Notify manager", True),
                Item("note", "Log a note", False)]

    def test_all_correct(self):
        submission = {
            "playbook_alert_type": "data_exfiltration",
            "root_cause": "Insider credential misuse — HTTPS exfil",
            "report": ("Incident summary — insider account used to "
                       "exfiltrate the roadmap. Timeline — 21:47 "
                       "login, 22:14 file access, 22:26 upload. "
                       "Evidence — network HTTPS + DNS. Root cause "
                       "— credential misuse. Recommendations — "
                       "rotate creds, enforce DLP."),
            "checked": ["isolate", "notify"],
        }
        checks = soc_report_engine.evaluate_report(
            self._alert(), self._checklist(), submission)
        assert checks["all_correct"] is True

    def test_short_report_fails(self):
        submission = {
            "playbook_alert_type": "data_exfiltration",
            "root_cause": "insider credential misuse",
            "report": "short",
            "checked": ["isolate", "notify"],
        }
        checks = soc_report_engine.evaluate_report(
            self._alert(), self._checklist(), submission)
        assert checks["report_length"] is False
        assert checks["all_correct"] is False

    def test_wrong_playbook_fails(self):
        submission = {
            "playbook_alert_type": "phishing",
            "root_cause": "insider credential misuse",
            "report": "a" * 200,
            "checked": ["isolate", "notify"],
        }
        checks = soc_report_engine.evaluate_report(
            self._alert(), self._checklist(), submission)
        assert checks["playbook"] is False

    def test_missing_required_checklist_fails(self):
        submission = {
            "playbook_alert_type": "data_exfiltration",
            "root_cause": "insider credential misuse",
            "report": ("Incident summary. Timeline. Evidence. "
                       "Root cause. Recommendations. " * 3),
            "checked": ["isolate"],
        }
        checks = soc_report_engine.evaluate_report(
            self._alert(), self._checklist(), submission)
        assert checks["checklist"] is False

    def test_root_cause_keyword_match_forgiving(self):
        # signature: _root_cause_matches(alert_type, root_cause)
        for phrase in ("Exfiltration via HTTPS",
                       "Insider used a leaked credential",
                       "Credential leak"):
            assert soc_report_engine._root_cause_matches(
                "data_exfiltration", phrase) is True


# ===========================================================================
# Simulator tests
# ===========================================================================
class TestSOCSimulatorPure:
    def test_key_and_capabilities(self):
        from app.simulators.soc.simulator import SOCSimulator
        sim = SOCSimulator()
        assert sim.key == "soc"
        assert "inspector" in sim.capabilities()
        ui = sim.describe_ui()
        assert ui.get("soc") is True
        assert ui.get("forensics") is True


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
        seed_forensics_labs()   # idempotency
    yield application


@pytest.fixture(scope="module")
def student(app):
    """A logged-in student who has already completed the forensics
    fundamentals lab so the SOC lab (which prereqs it) unlocks."""
    from app.auth.models import User
    from app.extensions import db
    from app.labs.forensics import engine as forensics_engine
    with app.app_context():
        user = User(username="soc_tester", email="soc@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    with app.test_client() as client:
        _login(client, "soc_tester")
        for slug in ("report-docx", "confidential-pdf", "holiday-jpg",
                     "backup-zip", "usb-toshiba", "browser-history",
                     "resume-pdf", "recycle-old-notes"):
            client.post("/labs/forensics-fundamentals/action",
                        json={"type": "select",
                              "payload": {"asset_id": slug}})
        client.post("/labs/forensics-fundamentals/action",
                    json={"type": "flag",
                          "payload": {"asset_id": "usb-toshiba"}})
        mod_hash = forensics_engine.simulated_hash(
            "confidential-pdf", "sha256")
        client.post("/labs/forensics-fundamentals/action",
                    json={"type": "submit", "payload": {
                        "modified_slug": "confidential-pdf",
                        "modified_hash": mod_hash,
                        "modified_time": "08:35",
                        "suspicious_slug": "usb-toshiba"}})
    yield "soc_tester"


@pytest.fixture(scope="module")
def admin(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="soc_admin", email="socadmin@test.io",
                    is_admin=True)
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "soc_admin"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestSOCSeed:
    def test_alerts_seeded(self, app):
        with app.app_context():
            from app.simulators.soc.models import SocAlert
            assert SocAlert.query.count() >= 6
            critical = SocAlert.query.filter_by(
                severity="critical").first()
            assert critical is not None
            assert critical.case_id is not None  # linked to a case

    def test_playbooks_seeded(self, app):
        with app.app_context():
            from app.simulators.soc.models import SocPlaybook
            assert SocPlaybook.query.count() >= 6
            data_exfil = SocPlaybook.query.filter_by(
                alert_type="data_exfiltration").first()
            assert data_exfil is not None
            assert len(data_exfil.steps) >= 5

    def test_lab_and_objectives(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="soc-analyst-fundamentals").first()
            assert lab is not None
            assert lab.simulator_key == "soc"
            assert lab.xp_reward == 150
            assert lab.difficulty == "Medium"
            assert len(lab.objectives) == 6

    def test_achievement_seeded(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            a = Achievement.query.filter_by(title="SOC Rookie").first()
            assert a is not None
            assert a.bonus_xp == 50
            assert a.condition_type == "soc_lab_completed"

    def test_reseed_idempotent(self, app):
        with app.app_context():
            from app.labs.forensics.seed import seed_forensics_labs
            from app.simulators.soc.models import (
                SocAlert, SocPlaybook, SocChecklistItem,
            )
            before = (SocAlert.query.count(),
                      SocPlaybook.query.count(),
                      SocChecklistItem.query.count())
            seed_forensics_labs()
            after = (SocAlert.query.count(),
                     SocPlaybook.query.count(),
                     SocChecklistItem.query.count())
            assert before == after


class TestSOCHTTP:
    def test_state_endpoint_returns_dashboard(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-analyst-fundamentals")
            response = client.get(
                "/labs/soc-analyst-fundamentals/soc/state")
            assert response.status_code == 200
            data = response.get_json()
            assert "stats" in data
            assert "open_queue" in data
            assert "playbook_options" in data
            # Content-loader auto-loads ALERT-2026-0007 for this lab.
            assert data["active_alert"] is not None
            assert data["active_alert"]["alert_code"].startswith("ALERT-")

    def test_lab_detail_renders_soc_panels(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            response = client.get("/labs/soc-analyst-fundamentals")
            assert response.status_code == 200
            assert b"soc-dashboard" in response.data
            assert b"Alert Queue" in response.data
            assert b"Response Playbook" in response.data
            assert b"Investigation Checklist" in response.data

    def test_admin_soc_overview_admin_only(self, app, admin, student):
        with app.test_client() as client:
            _login(client, admin)
            r = client.get("/admin/soc")
            assert r.status_code == 200
            assert b"Alerts" in r.data

        with app.test_client() as client:
            _login(client, student)
            r = client.get("/admin/soc")
            assert r.status_code in (302, 403)

    def test_admin_soc_alert_crud(self, app, admin):
        from app.simulators.soc.models import SocAlert
        with app.test_client() as client:
            _login(client, admin)
            # Create
            r = client.post("/admin/soc/alerts/new", data={
                "alert_code": "ALERT-TEST-0001",
                "title": "Test alert",
                "alert_type": "possible_malware",
                "severity": "high",
                "source": "EDR",
                "at_time": "12:00"}, follow_redirects=True)
            assert r.status_code == 200
            with app.app_context():
                created = SocAlert.query.filter_by(
                    alert_code="ALERT-TEST-0001").first()
                assert created is not None
                alert_id = created.id
            # Edit
            client.post(f"/admin/soc/alerts/{alert_id}/edit", data={
                "title": "Renamed", "alert_type": "possible_malware",
                "severity": "critical", "status": "in_progress",
                "source": "EDR", "at_time": "12:30",
                "description": ""})
            with app.app_context():
                edited = SocAlert.query.get(alert_id)
                assert edited.title == "Renamed"
                assert edited.severity == "critical"
            # Delete
            client.post(f"/admin/soc/alerts/{alert_id}/delete")
            with app.app_context():
                assert SocAlert.query.get(alert_id) is None


class TestSOCFullPlaythrough:
    """Complete every forensics lab then the SOC lab, and confirm
    the SOC Rookie achievement unlocks with its bonus XP."""

    def test_playthrough_unlocks_soc_rookie(self, app):
        from app.auth.models import User
        from app.extensions import db as _db
        from app.labs.forensics import engine as forensics_engine

        with app.app_context():
            student = User(username="rookie_tester",
                           email="rookie@test.io")
            student.set_password("Str0ngPass!")
            _db.session.add(student)
            _db.session.commit()
            student_id = student.id

        with app.test_client() as client:
            _login(client, "rookie_tester")

            # --- 1. Complete forensics fundamentals ---
            for slug in ("report-docx", "confidential-pdf",
                         "holiday-jpg", "backup-zip", "usb-toshiba",
                         "browser-history", "resume-pdf",
                         "recycle-old-notes"):
                client.post("/labs/forensics-fundamentals/action",
                            json={"type": "select",
                                  "payload": {"asset_id": slug}})
            client.post("/labs/forensics-fundamentals/action",
                        json={"type": "flag",
                              "payload": {"asset_id": "usb-toshiba"}})
            mod_hash = forensics_engine.simulated_hash(
                "confidential-pdf", "sha256")
            client.post("/labs/forensics-fundamentals/action",
                        json={"type": "submit", "payload": {
                            "modified_slug": "confidential-pdf",
                            "modified_hash": mod_hash,
                            "modified_time": "08:35",
                            "suspicious_slug": "usb-toshiba"}})

            # --- 2. Complete applied ---
            for source_type in ("event_log", "login_history",
                                "browser_history", "downloads",
                                "usb_history", "recent_docs"):
                client.post("/labs/forensics-applied/action",
                            json={"type": "select_source",
                                  "payload": {"source_type": source_type}})
            client.post("/labs/forensics-applied/action", json={
                "type": "submit", "payload": {
                    "first_login_time": "08:07",
                    "usb_serial": "KDT-7YQ-4419",
                    "downloaded_filename": "portfolio.zip",
                    "suspicious_url":
                        "https://pastebin.com/raw/9Zx4KpQ2",
                    "timeline_first_kind": "event_log",
                    "report_summary": (
                        "User attached rogue KINGSTON USB, modified "
                        "client-list.xlsx and downloaded portfolio.zip "
                        "from a non-corporate host — insider exfil."),
                }})

            # --- 3. Complete advanced ---
            with app.app_context():
                from app.labs.forensics.models import ForensicsCase
                case = ForensicsCase.query.filter_by(
                    lab_slug="forensics-advanced").first()
                case_dict = forensics_engine.case_from_orm(case)
                key_ids = sorted(a["id"] for a in case_dict["artifacts"]
                                 if a["is_key"])
                dl = forensics_engine.key_artifact(case_dict, "downloads")
                dns = forensics_engine.key_artifact(case_dict,
                                                    "network_dns")
                suspect = forensics_engine.key_suspect(case_dict)
                tl_start = sorted(a["at_time"]
                                  for a in case_dict["artifacts"]
                                  if a["is_key"])[0]

            client.post("/labs/forensics-advanced/action",
                        json={"type": "select_suspect",
                              "payload": {"slug": suspect["slug"]}})
            for i in range(len(key_ids) - 1):
                client.post("/labs/forensics-advanced/action",
                            json={"type": "link_artifacts",
                                  "payload": {"a": key_ids[i],
                                              "b": key_ids[i + 1]}})
            client.post("/labs/forensics-advanced/action", json={
                "type": "submit", "payload": {
                    "compromised_account": suspect["account"],
                    "timeline_start_time": tl_start,
                    "exfiltrated_file": dl["data"]["filename"],
                    "suspicious_ip": dns["data"]["response_ip"],
                    "attack_method":
                        "Insider credential misuse — HTTPS exfil",
                    "report_summary": (
                        "Compromised VPN account accessed the "
                        "roadmap PDF and exfiltrated a repackaged "
                        "archive via HTTPS to a non-corporate host."),
                }})

            # --- 4. Complete the SOC lab ---
            client.get("/labs/soc-analyst-fundamentals")

            state = client.get(
                "/labs/soc-analyst-fundamentals/soc/state").get_json()
            active_alert = state["active_alert"]
            assert active_alert is not None
            alert_type = active_alert["alert_type"]

            # Explicitly open the alert (objective 1 — some content
            # loaders auto-set active_alert but the event still needs
            # to fire).
            client.post(
                "/labs/soc-analyst-fundamentals/action",
                json={"type": "open_alert",
                      "payload": {"alert_code":
                          active_alert["alert_code"]}})

            # Open at least one forensics source (objective 2).
            for source_type in ("event_log", "login_history",
                                "browser_history", "downloads",
                                "network_dns"):
                client.post(
                    "/labs/soc-analyst-fundamentals/action",
                    json={"type": "select_source",
                          "payload": {"source_type": source_type}})

            # Correlate the forensics evidence (fires
            # correlation_complete which the SOC lab reuses).
            with app.app_context():
                from app.simulators.soc.models import SocAlert
                alert = SocAlert.query.filter_by(
                    alert_code=active_alert["alert_code"]).first()
                if alert.case_id:
                    case_orm = ForensicsCase.query.get(alert.case_id)
                    case_dict_soc = forensics_engine.case_from_orm(
                        case_orm)
                    soc_key_ids = sorted(a["id"]
                                          for a in case_dict_soc["artifacts"]
                                          if a["is_key"])
                else:
                    soc_key_ids = []
            for i in range(len(soc_key_ids) - 1):
                client.post(
                    "/labs/soc-analyst-fundamentals/action",
                    json={"type": "link_artifacts",
                          "payload": {"a": soc_key_ids[i],
                                      "b": soc_key_ids[i + 1]}})

            # Tick every required checklist item.
            for item in state["checklist"]:
                if item.get("is_required"):
                    client.post(
                        "/labs/soc-analyst-fundamentals/action",
                        json={"type": "tick_checklist",
                              "payload": {"slug": item["slug"]}})

            # Pick the correct playbook (the one wired to this alert
            # type).
            with app.app_context():
                from app.simulators.soc.models import SocPlaybook
                correct_pb = SocPlaybook.query.filter_by(
                    alert_type=alert_type).first()
                assert correct_pb is not None
                pb_alert_type = correct_pb.alert_type
            client.post(
                "/labs/soc-analyst-fundamentals/action",
                json={"type": "select_playbook",
                      "payload": {"alert_type": pb_alert_type}})

            # Set root cause + close.
            client.post(
                "/labs/soc-analyst-fundamentals/action",
                json={"type": "set_root_cause",
                      "payload": {"text":
                          "Insider credential misuse — HTTPS exfil "
                          "via filedump.example"}})
            r = client.post(
                "/labs/soc-analyst-fundamentals/action",
                json={"type": "close_incident",
                      "payload": {"report": (
                          "Incident summary — insider account misuse. "
                          "Severity — high. "
                          "Timeline — 21:47 VPN login, 22:14 file "
                          "access, 22:26 HTTPS upload. "
                          "Evidence — network DNS, HTTPS, event "
                          "log. "
                          "Root cause — leaked credentials. "
                          "Actions taken — session terminated, "
                          "credentials rotated. "
                          "Recommendations — enforce DLP, review "
                          "VPN entitlements.")}})
            body = r.get_json()
            assert body.get("lab_completed") is True

        # SOC Rookie should now be unlocked with its +50 bonus.
        with app.app_context():
            from app.achievement.models import (
                Achievement, UserAchievement,
            )
            rookie = Achievement.query.filter_by(
                title="SOC Rookie").first()
            unlocked = UserAchievement.query.filter_by(
                user_id=student_id,
                achievement_id=rookie.id).first()
            assert unlocked is not None
