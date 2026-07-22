"""Tests for YC-029.5.2 — Digital Forensics: Fundamentals.

Covers:
  · engine  — deterministic simulated hashes, metadata builder,
              findings evaluation.
  · simulator — bootstrap, select/flag/submit action loop, event
              emission (drives the objective validators).
  · seed    — idempotent by slug/title, category + engine + lab + 5
              objectives + First Investigator achievement present.
  · HTTP    — the forensics state endpoint, admin case list/edit,
              lab detail renders without a terminal.
  · achievement — completing every objective unlocks First Investigator
              and awards the bonus XP through the existing engine.
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc02952-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_forensics.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.labs.forensics import engine  # noqa: E402
from app.labs.forensics.simulator import ForensicsSimulator  # noqa: E402
from app.labs.simulator_base import Action  # noqa: E402


# ===========================================================================
# Pure engine tests
# ===========================================================================
class TestHash:
    def test_deterministic(self):
        h1 = engine.simulated_hash("confidential-pdf", "sha256")
        h2 = engine.simulated_hash("confidential-pdf", "sha256")
        assert h1 == h2

    def test_sha256_and_md5_lengths(self):
        assert len(engine.simulated_hash("x", "sha256")) == 64
        assert len(engine.simulated_hash("x", "md5")) == 32

    def test_different_slugs_produce_different_hashes(self):
        a = engine.simulated_hash("confidential-pdf", "sha256")
        b = engine.simulated_hash("report-docx", "sha256")
        assert a != b

    def test_algorithm_defaults_to_sha256_shape(self):
        # Unknown algorithm still returns 64-char hex — never crashes.
        h = engine.simulated_hash("x", "whirlpool")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestFormatSize:
    def test_bytes(self):
        assert engine.format_size(500) == "500 B"

    def test_kb(self):
        assert engine.format_size(2048).endswith("KB")

    def test_mb(self):
        assert engine.format_size(3 * 1024 * 1024).endswith("MB")


# A minimal case dict used by the engine/simulator tests.
CASE = {
    "id": 1, "lab_slug": "forensics-fundamentals",
    "title": "Test case", "briefing": "b",
    "workstation_name": "WS-01", "investigator": "Investigator",
    "evidence": [
        {"slug": "report", "kind": "document", "filename": "report.docx",
         "extension": "docx", "owner": "user", "size_bytes": 1024,
         "created_at_display": "10:00", "modified_at_display": "10:00",
         "notes": "", "is_suspicious": False, "is_modified": False,
         "display_order": 1},
        {"slug": "leak", "kind": "pdf", "filename": "leak.pdf",
         "extension": "pdf", "owner": "user", "size_bytes": 2048,
         "created_at_display": "09:00", "modified_at_display": "10:15",
         "notes": "", "is_suspicious": False, "is_modified": True,
         "display_order": 2},
        {"slug": "rogue-usb", "kind": "usb", "filename": "ROGUE (E:)",
         "extension": "", "owner": "system", "size_bytes": 0,
         "created_at_display": "09:55", "modified_at_display": "09:55",
         "notes": "", "is_suspicious": True, "is_modified": False,
         "display_order": 3},
    ],
    "timeline": [
        {"at_time": "09:00", "kind": "login",
         "description": "Login", "evidence_slug": None},
        {"at_time": "09:55", "kind": "usb",
         "description": "USB connected", "evidence_slug": "rogue-usb"},
        {"at_time": "10:15", "kind": "file_modified",
         "description": "leak.pdf modified", "evidence_slug": "leak"},
    ],
}


class TestEvaluateFindings:
    def _correct(self):
        return {
            "modified_slug": "leak",
            "modified_hash": engine.simulated_hash("leak", "sha256"),
            "modified_time": "10:15",
            "suspicious_slug": "rogue-usb",
        }

    def test_all_correct(self):
        checks = engine.evaluate_findings(CASE, self._correct())
        assert checks["all_correct"] is True

    def test_wrong_slug(self):
        payload = self._correct()
        payload["modified_slug"] = "report"
        checks = engine.evaluate_findings(CASE, payload)
        assert checks["modified_slug"] is False
        assert checks["all_correct"] is False

    def test_wrong_hash(self):
        payload = self._correct()
        payload["modified_hash"] = "0" * 64
        checks = engine.evaluate_findings(CASE, payload)
        assert checks["modified_hash"] is False
        assert checks["all_correct"] is False

    def test_wrong_time(self):
        payload = self._correct()
        payload["modified_time"] = "09:00"
        checks = engine.evaluate_findings(CASE, payload)
        assert checks["modified_time"] is False

    def test_case_insensitive_hash(self):
        payload = self._correct()
        payload["modified_hash"] = payload["modified_hash"].upper()
        checks = engine.evaluate_findings(CASE, payload)
        assert checks["modified_hash"] is True

    def test_missing_fields_fail_cleanly(self):
        checks = engine.evaluate_findings(CASE, {})
        assert checks["all_correct"] is False


class TestBuildView:
    def test_groups_by_kind(self):
        view = engine.build_view(CASE)
        assert "usb" in view["grouped"]
        assert "pdf" in view["grouped"]
        assert view["case_title"] == "Test case"

    def test_metadata_panel(self):
        meta = engine.evidence_metadata(CASE["evidence"][1])
        assert meta.filename == "leak.pdf"
        assert len(meta.sha256) == 64
        assert len(meta.md5) == 32


# ===========================================================================
# Simulator tests
# ===========================================================================
class TestSimulator:
    def _sim_state(self):
        sim = ForensicsSimulator()
        state = sim.bootstrap(None, {"case": CASE})
        return sim, state

    def test_bootstrap_envelope(self):
        sim, state = self._sim_state()
        assert state["sim"] == "forensics"
        assert state["selected"] is None
        assert state["inspected"] == []
        assert state["flagged"] == []

    def test_capabilities_inspector(self):
        sim = ForensicsSimulator()
        assert sim.capabilities() == {"inspector"}
        assert sim.describe_ui()["forensics"] is True

    def test_select_emits_inspected(self):
        sim, state = self._sim_state()
        result = sim.handle(state, Action("select", {"asset_id": "leak"}))
        assert result.new_state["selected"] == "leak"
        assert any(e["type"] == "evidence_inspected"
                   for e in result.events)
        assert "leak" in result.new_state["inspected"]

    def test_select_unknown_slug(self):
        sim, state = self._sim_state()
        result = sim.handle(state, Action("select", {"asset_id": "xxx"}))
        assert "No evidence" in result.output
        assert result.new_state.get("selected") is None

    def test_all_evidence_inspected(self):
        sim, state = self._sim_state()
        events: list = []
        for e in CASE["evidence"]:
            r = sim.handle(state, Action("select", {"asset_id": e["slug"]}))
            state = r.new_state
            events.extend(r.events)
        assert any(e["type"] == "all_evidence_inspected" for e in events)

    def test_flag_toggle_and_suspicious(self):
        sim, state = self._sim_state()
        r1 = sim.handle(state, Action("flag", {"asset_id": "rogue-usb"}))
        assert "rogue-usb" in r1.new_state["flagged"]
        assert any(e["type"] == "suspicious_flagged" for e in r1.events)

        r2 = sim.handle(r1.new_state,
                        Action("flag", {"asset_id": "rogue-usb"}))
        assert "rogue-usb" not in r2.new_state["flagged"]

    def test_submit_correct_findings(self):
        sim, state = self._sim_state()
        r = sim.handle(state, Action("submit", {
            "modified_slug": "leak",
            "modified_hash": engine.simulated_hash("leak", "sha256"),
            "modified_time": "10:15",
            "suspicious_slug": "rogue-usb"}))
        assert r.new_state["findings_correct"] is True
        assert any(e["type"] == "findings_correct" for e in r.events)

    def test_submit_wrong_findings(self):
        sim, state = self._sim_state()
        r = sim.handle(state, Action("submit", {"modified_slug": ""}))
        assert r.new_state["findings_correct"] is False
        assert any(e["type"] == "findings_incorrect" for e in r.events)

    def test_status_panel_reflects_progress(self):
        sim, state = self._sim_state()
        panel = sim.status_panel(state)
        labels = {i["label"] for i in panel}
        assert {"Case", "Evidence", "Inspected", "Flagged",
                "Findings"} <= labels


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
        seed_forensics_labs()  # idempotency
    yield application


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="fx_tester", email="fx@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "fx_tester"


@pytest.fixture(scope="module")
def admin(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="fx_admin", email="fxadmin@test.io",
                    is_admin=True)
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "fx_admin"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestSeed:
    def test_case_present(self, app):
        with app.app_context():
            from app.labs.forensics.models import ForensicsCase
            case = ForensicsCase.query.filter_by(
                lab_slug="forensics-fundamentals").first()
            assert case is not None
            assert len(case.evidence) == 8
            assert len(case.timeline) == 7

    def test_lab_and_objectives(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="forensics-fundamentals").first()
            assert lab is not None
            assert lab.simulator_key == "forensics"
            assert lab.xp_reward == 50
            assert lab.difficulty == "Easy"
            assert len(lab.objectives) == 5

    def test_achievement_seeded(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            a = Achievement.query.filter_by(
                title="First Investigator").first()
            assert a is not None
            assert a.bonus_xp == 25
            assert a.condition_type == "forensics_lab_completed"

    def test_reseed_is_idempotent(self, app):
        with app.app_context():
            from app.labs.forensics.models import (
                ForensicsCase, ForensicsEvidence,
            )
            from app.labs.forensics.seed import seed_forensics_labs
            before = ForensicsCase.query.count()
            before_ev = ForensicsEvidence.query.count()
            seed_forensics_labs()
            assert ForensicsCase.query.count() == before
            assert ForensicsEvidence.query.count() == before_ev


class TestHTTP:
    def test_lab_detail_renders_without_terminal(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            response = client.get("/labs/forensics-fundamentals")
            assert response.status_code == 200
            # No terminal input row for inspector-only labs.
            assert b"lw-inputrow" not in response.data
            # Forensics workspace is present.
            assert b"fx-explorer" in response.data
            assert b"Findings Report" in response.data

    def test_forensics_state_endpoint(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/forensics-fundamentals")  # start session
            response = client.get(
                "/labs/forensics-fundamentals/forensics/state")
            assert response.status_code == 200
            data = response.get_json()
            assert "view" in data and "metadata" in data["view"]
            assert data["view"]["metadata"]["confidential-pdf"]["sha256"]

    def test_admin_case_list(self, app, admin):
        with app.test_client() as client:
            _login(client, admin)
            response = client.get("/admin/forensics")
            assert response.status_code == 200
            assert b"forensics-fundamentals" in response.data

    def test_admin_case_edit_renders(self, app, admin):
        with app.app_context():
            from app.labs.forensics.models import ForensicsCase
            case_id = ForensicsCase.query.filter_by(
                lab_slug="forensics-fundamentals").first().id
        with app.test_client() as client:
            _login(client, admin)
            response = client.get(f"/admin/forensics/{case_id}")
            assert response.status_code == 200
            assert b"Case briefing" in response.data
            assert b"Evidence" in response.data

    def test_non_admin_blocked_from_admin_pages(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            response = client.get("/admin/forensics")
            assert response.status_code in (302, 403)


class TestFullPlaythrough:
    """Drive the whole lab through the real action endpoint, then
    verify XP was awarded and the First Investigator achievement
    unlocked with its bonus XP."""

    def test_playthrough_awards_xp_and_achievement(self, app, student):
        from app.auth.models import User

        with app.test_client() as client:
            _login(client, student)
            # Initial XP snapshot
            with app.app_context():
                user_before = User.query.filter_by(
                    username=student).first()
                xp_before = user_before.xp

            def _act(action_type, payload):
                return client.post(
                    "/labs/forensics-fundamentals/action",
                    json={"type": action_type, "payload": payload})

            # Inspect every evidence item (objective 1).
            with app.app_context():
                from app.labs.forensics.models import ForensicsCase
                case = ForensicsCase.query.filter_by(
                    lab_slug="forensics-fundamentals").first()
                slugs = [e.slug for e in case.evidence]
                mod_hash = engine.simulated_hash("confidential-pdf",
                                                 "sha256")
            for slug in slugs:
                r = _act("select", {"asset_id": slug})
                assert r.status_code == 200

            # Flag the suspicious USB (objective 4).
            r = _act("flag", {"asset_id": "usb-toshiba"})
            assert r.status_code == 200

            # Submit correct findings (objectives 2, 3, 5).
            r = _act("submit", {
                "modified_slug": "confidential-pdf",
                "modified_hash": mod_hash,
                "modified_time": "08:35",
                "suspicious_slug": "usb-toshiba",
            })
            assert r.status_code == 200
            body = r.get_json()
            assert body.get("lab_completed") is True

            # XP awarded + achievement unlocked with bonus XP.
            with app.app_context():
                user_after = User.query.filter_by(
                    username=student).first()
                assert user_after.xp > xp_before
                from app.achievement.models import (
                    Achievement, UserAchievement,
                )
                first_inv = Achievement.query.filter_by(
                    title="First Investigator").first()
                unlocked = UserAchievement.query.filter_by(
                    user_id=user_after.id,
                    achievement_id=first_inv.id).first()
                assert unlocked is not None
                # Bonus 25 XP from achievement + 50 lab XP + 50 objective XP.
                assert (user_after.xp - xp_before) >= 25


# ===========================================================================
# YC-029.5.3 — Applied lab (extra tests, layered on the same throwaway app)
# ===========================================================================
APPLIED_CASE = {
    "id": 99, "lab_slug": "forensics-applied", "mode": "applied",
    "title": "Applied test",
    "briefing": "", "workstation_name": "WS", "investigator": "I",
    "evidence": [],
    "timeline": [
        {"at_time": "08:00", "kind": "login",
         "description": "Session start", "evidence_slug": None},
    ],
    "artifacts": [
        {"id": 1, "source_type": "event_log", "at_time": "07:59",
         "data": {"event_id": 4624, "description": "Login"},
         "is_key": False, "sort_order": 1},
        {"id": 2, "source_type": "login_history", "at_time": "08:00",
         "data": {"username": "u", "login_at": "08:00",
                  "logout_at": "16:00", "duration": "08h"},
         "is_key": True, "sort_order": 2},
        {"id": 3, "source_type": "browser_history", "at_time": "10:30",
         "data": {"url": "https://evil.example/leak",
                  "title": "Leak", "visit_count": 1},
         "is_key": True, "sort_order": 3},
        {"id": 4, "source_type": "downloads", "at_time": "10:35",
         "data": {"filename": "steal.zip",
                  "url": "https://evil.example/steal.zip",
                  "size_bytes": 1024},
         "is_key": True, "sort_order": 4},
        {"id": 5, "source_type": "usb_history", "at_time": "10:00",
         "data": {"device_name": "ROGUE (F:)",
                  "serial_number": "RG-XYZ-1234",
                  "connected_at": "10:00", "removed_at": "16:30"},
         "is_key": True, "sort_order": 5},
        {"id": 6, "source_type": "recent_docs", "at_time": "12:00",
         "data": {"filename": "n.txt", "path": "C:\\n.txt",
                  "last_accessed_at": "12:00"},
         "is_key": False, "sort_order": 6},
    ],
}


class TestAppliedEngine:
    def test_all_sources_lists_present_ones(self):
        sources = engine.all_sources(APPLIED_CASE)
        types = {s["source_type"] for s in sources}
        assert types == {"event_log", "login_history", "browser_history",
                         "downloads", "usb_history", "recent_docs"}

    def test_artifacts_by_source_sorted(self):
        rows = engine.artifacts_by_source(APPLIED_CASE, "event_log")
        assert len(rows) == 1
        assert rows[0]["source_type"] == "event_log"

    def test_unified_timeline_merges_and_sorts(self):
        merged = engine.unified_timeline(APPLIED_CASE)
        # 1 timeline + 6 artifacts = 7 rows.
        assert len(merged) == 7
        # Sorted by at_time — the earliest is the 07:59 event_log row.
        assert merged[0]["at_time"] == "07:59"
        assert merged[0]["source"] == "event_log"

    def test_key_artifact_lookup(self):
        assert engine.key_artifact(APPLIED_CASE,
                                    "usb_history")["id"] == 5
        assert engine.key_artifact(APPLIED_CASE, "event_log") is None

    def test_evaluate_applied_findings_all_correct(self):
        payload = {
            "first_login_time": "08:00",
            "usb_serial": "RG-XYZ-1234",
            "downloaded_filename": "steal.zip",
            "suspicious_url": "https://evil.example/leak",
            "timeline_first_kind": "event_log",
            "report_summary":
                "The user attached a rogue USB, downloaded a stolen "
                "archive and leaked via evil.example.",
        }
        checks = engine.evaluate_applied_findings(APPLIED_CASE, payload)
        assert checks["all_correct"] is True

    def test_report_summary_too_short_fails(self):
        payload = {
            "first_login_time": "08:00",
            "usb_serial": "RG-XYZ-1234",
            "downloaded_filename": "steal.zip",
            "suspicious_url": "https://evil.example/leak",
            "timeline_first_kind": "event_log",
            "report_summary": "tl;dr — bad.",
        }
        checks = engine.evaluate_applied_findings(APPLIED_CASE, payload)
        assert checks["report"] is False
        assert checks["all_correct"] is False


class TestAppliedSimulator:
    def _sim_state(self):
        sim = ForensicsSimulator()
        return sim, sim.bootstrap(None, {"case": APPLIED_CASE})

    def test_select_source_records_and_fires_all_sources(self):
        sim, state = self._sim_state()
        events = []
        for source_type in ("event_log", "login_history",
                            "browser_history", "downloads",
                            "usb_history", "recent_docs"):
            r = sim.handle(state, Action("select_source",
                                          {"source_type": source_type}))
            state = r.new_state
            events.extend(r.events)
        assert any(e["type"] == "all_sources_opened" for e in events)
        assert state["active_source"] == "recent_docs"

    def test_select_artifact_records_key_flag(self):
        sim, state = self._sim_state()
        r = sim.handle(state, Action("select_artifact",
                                      {"artifact_id": 5}))
        assert 5 in r.new_state["seen_artifacts"]
        assert any(e["type"] == "key_artifact_inspected"
                   for e in r.events)

    def test_select_artifact_unknown(self):
        sim, state = self._sim_state()
        r = sim.handle(state, Action("select_artifact",
                                      {"artifact_id": 9999}))
        assert "No artifact" in r.output

    def test_submit_routes_to_applied(self):
        sim, state = self._sim_state()
        r = sim.handle(state, Action("submit", {
            "first_login_time": "08:00",
            "usb_serial": "RG-XYZ-1234",
            "downloaded_filename": "steal.zip",
            "suspicious_url": "https://evil.example/leak",
            "timeline_first_kind": "event_log",
            "report_summary":
                "The user attached a rogue USB, downloaded a stolen "
                "archive and leaked via evil.example.",
        }))
        assert r.new_state["findings_correct"] is True
        types = [e["type"] for e in r.events]
        assert "findings_correct" in types
        assert "report_submitted" in types


# ===========================================================================
# Applied lab — end-to-end integration (real seed, real routes)
# ===========================================================================
class TestAppliedSeedAndHTTP:
    def test_applied_lab_seeded(self, app):
        with app.app_context():
            from app.labs.forensics.models import ForensicsCase
            case = ForensicsCase.query.filter_by(
                lab_slug="forensics-applied").first()
            assert case is not None
            assert case.mode == "applied"
            # 6 sources × ≥2 rows each.
            assert len(case.artifacts) >= 12

    def test_correlator_achievement_seeded(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            a = Achievement.query.filter_by(
                title="Evidence Correlator").first()
            assert a is not None
            assert a.bonus_xp == 50
            assert a.condition_value == 2

    def test_applied_lab_shape(self, app):
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(
                slug="forensics-applied").first()
            assert lab is not None
            assert lab.xp_reward == 100
            assert lab.difficulty == "Medium"
            assert len(lab.objectives) == 6

    def test_state_endpoint_exposes_applied_view(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/forensics-applied")
            response = client.get(
                "/labs/forensics-applied/forensics/state")
            assert response.status_code == 200
            data = response.get_json()
            assert data["view"]["mode"] == "applied"
            assert len(data["view"]["sources"]) == 6
            assert len(data["view"]["unified_timeline"]) >= 7
            assert "browser_history" in data["view"]["schema"]

    def test_applied_playthrough_unlocks_correlator(self, app):
        """Second forensics lab completion unlocks Evidence Correlator
        (+50 bonus XP). Uses a fresh student so the achievement
        engine sees `forensics_labs_completed` climb 0 → 2."""
        from app.auth.models import User
        from app.extensions import db as _db
        with app.app_context():
            student = User(username="applied_tester",
                           email="ap@test.io")
            student.set_password("Str0ngPass!")
            _db.session.add(student)
            _db.session.commit()
            student_id = student.id

        with app.test_client() as client:
            _login(client, "applied_tester")

            # --- 1. Complete the fundamentals lab first ---
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
            mod_hash = engine.simulated_hash("confidential-pdf",
                                              "sha256")
            client.post("/labs/forensics-fundamentals/action",
                        json={"type": "submit", "payload": {
                            "modified_slug": "confidential-pdf",
                            "modified_hash": mod_hash,
                            "modified_time": "08:35",
                            "suspicious_slug": "usb-toshiba"}})

            # --- 2. Complete the applied lab ---
            for source_type in ("event_log", "login_history",
                                "browser_history", "downloads",
                                "usb_history", "recent_docs"):
                r = client.post(
                    "/labs/forensics-applied/action",
                    json={"type": "select_source",
                          "payload": {"source_type": source_type}})
                assert r.status_code == 200

            r = client.post("/labs/forensics-applied/action", json={
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
            body = r.get_json()
            assert body.get("lab_completed") is True

        with app.app_context():
            from app.achievement.models import (
                Achievement, UserAchievement,
            )
            correlator = Achievement.query.filter_by(
                title="Evidence Correlator").first()
            unlocked = UserAchievement.query.filter_by(
                user_id=student_id,
                achievement_id=correlator.id).first()
            assert unlocked is not None
