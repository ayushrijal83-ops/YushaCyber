"""Tests for YC-030.6 — Threat Hunting Dashboard.

Covers:
  · hunt_engine   — search, IOC filter, related evidence, bookmarks,
                    structured notes, MITRE mapping, report scoring
  · simulator     — search_telemetry, bookmark, map_mitre,
                    add_hunt_note, submit_hunt_report actions
  · seed          — 6 hunt labs, MITRE registered, achievement
  · HTTP          — state endpoint includes hunt state
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0306-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_hunt.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.simulators.soc import hunt_engine  # noqa: E402


# ===========================================================================
# Pure engine tests
# ===========================================================================
SAMPLE_ARTIFACTS = [
    {"id": 1, "source_type": "network_dns", "at_time": "23:00",
     "data": {"query": "exfil.example", "response_ip": "198.51.100.44",
              "domain": "exfil.example"}, "is_key": True},
    {"id": 2, "source_type": "ioc_ip", "at_time": "23:00",
     "data": {"ip": "198.51.100.44", "reputation": "malicious",
              "geo": "Unknown", "first_seen": "2026-08-01"}, "is_key": True},
    {"id": 3, "source_type": "event_log", "at_time": "02:00",
     "data": {"event_id": 4688, "description": "powershell.exe -enc"},
     "is_key": True},
    {"id": 4, "source_type": "ioc_domain", "at_time": "23:00",
     "data": {"domain": "exfil.example", "reputation": "malicious"},
     "is_key": True},
]


class TestSearch:
    def test_search_by_query(self):
        results = hunt_engine.search_telemetry(
            SAMPLE_ARTIFACTS, "exfil.example")
        assert len(results) >= 2  # DNS + IOC domain

    def test_search_by_field(self):
        results = hunt_engine.search_telemetry(
            SAMPLE_ARTIFACTS, "198.51.100.44", field="ip")
        assert len(results) == 1
        assert results[0]["source_type"] == "ioc_ip"

    def test_search_empty_query(self):
        assert hunt_engine.search_telemetry(SAMPLE_ARTIFACTS, "") == []

    def test_search_no_match(self):
        assert hunt_engine.search_telemetry(
            SAMPLE_ARTIFACTS, "nonexistent") == []


class TestIOC:
    def test_ioc_filter(self):
        iocs = hunt_engine.ioc_artifacts(SAMPLE_ARTIFACTS)
        assert all(a["source_type"].startswith("ioc_") for a in iocs)
        assert len(iocs) == 2

    def test_related_evidence(self):
        related = hunt_engine.related_evidence(
            SAMPLE_ARTIFACTS, "198.51.100.44")
        assert len(related) >= 2  # DNS + IOC IP


class TestBookmarks:
    def test_add_and_remove(self):
        state = {}
        state = hunt_engine.add_bookmark(state, "artifact-1", "DNS query")
        assert len(state["hunt_bookmarks"]) == 1
        # Idempotent
        state = hunt_engine.add_bookmark(state, "artifact-1", "DNS query")
        assert len(state["hunt_bookmarks"]) == 1
        state = hunt_engine.remove_bookmark(state, "artifact-1")
        assert len(state["hunt_bookmarks"]) == 0


class TestStructuredNotes:
    def test_add_note(self):
        state = {}
        state = hunt_engine.add_hunt_note(state, {
            "title": "Suspicious DNS",
            "observation": "High frequency TXT queries detected.",
            "evidence": "HUNT-002 DNS artifacts",
            "priority": "high",
            "recommendation": "Block domain and investigate."})
        assert len(state["hunt_notes"]) == 1
        assert state["hunt_notes"][0]["title"] == "Suspicious DNS"


class TestMITRE:
    def test_register_and_get(self):
        hunt_engine.register_mitre("TEST-HUNT", [
            {"tactic": "execution", "technique_id": "T1059",
             "technique_name": "PowerShell"}])
        mapping = hunt_engine.get_mitre("TEST-HUNT")
        assert len(mapping) == 1
        assert mapping[0]["technique_id"] == "T1059"

    def test_mitre_summary_groups_by_tactic(self):
        hunt_engine.register_mitre("TEST-HUNT-2", [
            {"tactic": "execution", "technique_id": "T1059",
             "technique_name": "PowerShell"},
            {"tactic": "persistence", "technique_id": "T1053",
             "technique_name": "Scheduled Task"},
        ])
        summary = hunt_engine.mitre_summary("TEST-HUNT-2")
        assert len(summary) == 2
        assert summary[0]["tactic"] == "execution"
        assert summary[1]["tactic"] == "persistence"

    def test_empty_hunt_returns_empty(self):
        assert hunt_engine.get_mitre("NONEXISTENT") == []


class TestHuntScoring:
    def test_excellent_score(self):
        score = hunt_engine.score_hunt_report(
            "Executive summary of the hunt hypothesis. "
            "Evidence collected from DNS and process logs. "
            "Findings show C2 beaconing pattern. "
            "MITRE ATT&CK techniques mapped. "
            "Recommendations include blocking the domain.",
            iocs_found=5, mitre_mapped=5,
            bookmarks_count=5, hints_used=0)
        assert score["rating"] == "Excellent"

    def test_hint_penalty(self):
        score_no = hunt_engine.score_hunt_report(
            "x" * 200, 3, 3, 3, hints_used=0)
        score_yes = hunt_engine.score_hunt_report(
            "x" * 200, 3, 3, 3, hints_used=5)
        assert score_yes["total"] < score_no["total"]

    def test_fail_on_empty(self):
        score = hunt_engine.score_hunt_report("short", 0, 0, 0)
        assert score["rating"] == "Fail"


# ===========================================================================
# Integration tests
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
        user = User(username="hunt_tester", email="hunt@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "hunt_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestHuntSeed:
    def test_six_hunts_seeded(self, app):
        with app.app_context():
            from app.labs.models import Lab
            labs = Lab.query.filter(
                Lab.slug.like("soc-hunt-%")).all()
            assert len(labs) == 6
            for lab in labs:
                assert lab.xp_reward == 250
                assert lab.difficulty == "Expert"
                assert len(lab.objectives) == 6

    def test_mitre_registered_for_all(self, app):
        with app.app_context():
            for code in ("HUNT-001", "HUNT-002", "HUNT-003",
                         "HUNT-004", "HUNT-005", "HUNT-006"):
                mitre = hunt_engine.get_mitre(code)
                assert len(mitre) >= 2, f"{code} missing MITRE"

    def test_achievement_seeded(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            a = Achievement.query.filter_by(
                title="Threat Hunter Elite").first()
            assert a is not None
            assert a.bonus_xp == 150

    def test_reseed_idempotent(self, app):
        with app.app_context():
            from app.labs.forensics.seed import seed_forensics_labs
            from app.labs.models import Lab
            before = Lab.query.filter(
                Lab.slug.like("soc-hunt-%")).count()
            seed_forensics_labs()
            after = Lab.query.filter(
                Lab.slug.like("soc-hunt-%")).count()
            assert before == after


class TestHuntHTTP:
    def test_state_includes_hunt_fields(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-hunt-powershell")
            r = client.get(
                "/labs/soc-hunt-powershell/soc/state")
            assert r.status_code == 200
            data = r.get_json()
            assert "hunt_bookmarks" in data
            assert "hunt_notes" in data
            assert "hunt_mitre_mapped" in data
            assert "hunt_mitre_summary" in data
            assert len(data["hunt_mitre_summary"]) >= 1

    def test_search_action(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-hunt-dns")
            r = client.post(
                "/labs/soc-hunt-dns/action",
                json={"type": "search_telemetry",
                      "payload": {"query": "exfil.example"}})
            assert r.status_code == 200
            assert "result" in r.get_json().get("output", "").lower()

    def test_bookmark_action(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            client.get("/labs/soc-hunt-creds")
            r = client.post(
                "/labs/soc-hunt-creds/action",
                json={"type": "bookmark",
                      "payload": {"ref": "artifact-1",
                                  "label": "LSASS dump"}})
            assert r.status_code == 200
            assert "bookmark" in r.get_json().get("output", "").lower()
