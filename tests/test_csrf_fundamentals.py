"""Tests for YC-035.6 — Cross-Site Request Forgery (CSRF) Fundamentals mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0356-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_csrf.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell
from app.core.terminal.web import (
    ATTACKER_ORIGIN,
    HOST,
    TRUSTED_ORIGIN,
    WebApp,
    _csrf_token_for_session,
    build_request,
    build_web_lab,
    parse_url,
)

STUDENT_SID = "student-session"
VALID_TOKEN = _csrf_token_for_session(STUDENT_SID)

SOLVE: list[str] = [
    "web",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login',
    "open https://cybershop.training/account",
    'open -X POST -d "recipient=training-user&amount=100" https://cybershop.training/transfer',
    "intercept on",
    'open -X POST -d "recipient=training-user&amount=50" https://cybershop.training/transfer',
    "forward",
    "intercept off",
    "open https://cybershop.training/csrf-demo",
    ('open -X POST -H "Origin: https://attacker.training" '
     '-H "Referer: https://attacker.training/" '
     '-d "recipient=training-user&amount=100" https://cybershop.training/transfer'),
    "open https://cybershop.training/transfer",
    "open https://cybershop.training/secure-transfer",
    'open -X POST -d "recipient=training-user&amount=100" https://cybershop.training/secure-transfer',
    ('open -X POST -d "recipient=training-user&amount=100&csrf_token=INVALID_TRAINING_TOKEN" '
     "https://cybershop.training/secure-transfer"),
    (f'open -X POST -d "recipient=training-user&amount=100&csrf_token={VALID_TOKEN}" '
     "https://cybershop.training/secure-transfer"),
    "samesite strict",
    "samesite lax",
    "samesite none",
    (f'open -X POST -H "Origin: https://attacker.training" '
     f'-d "recipient=training-user&amount=100&csrf_token={VALID_TOKEN}" '
     "https://cybershop.training/secure-transfer"),
    "evidence",
    "inspect 1", "inspect 2", "inspect 3", "inspect 4", "inspect 5",
    ('echo "Conclusion: the vulnerable transfer endpoint trusted the session cookie '
     "alone and accepted a forged-looking cross-site request - this is CSRF. The "
     "secure endpoint rejected the same request shape and only succeeded once the "
     "correct anti-csrf token was included, proving a synchronizer token is the "
     'correct defensive control." > web/csrf-investigation.txt'),
]


# ═══════════════════════════════════════════
# WebApp routing — new/extended routes
# ═══════════════════════════════════════════
class TestWebAppRouting:
    def _get(self, app, path, cookies=None):
        url = parse_url(f"https://{HOST}{path}")
        req = build_request("GET", url, cookies=cookies or {})
        return req, app.handle(req)

    def _login(self, app):
        url = parse_url(f"https://{HOST}/auth/login")
        req = build_request("POST", url, body="username=student&password=training123")
        resp = app.handle(req)
        return resp.cookies["session_id"]

    def test_settings_requires_auth(self):
        app = WebApp()
        _, resp = self._get(app, "/settings")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login"

    def test_settings_authenticated(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._get(app, "/settings", {"session_id": sid})
        assert resp.status_code == 200
        assert "student" in resp.body

    def test_csrf_demo_describes_vulnerable_endpoint(self):
        app = WebApp()
        _, resp = self._get(app, "/csrf-demo")
        assert resp.status_code == 200
        assert "/transfer" in resp.body
        assert "session cookie" in resp.body.lower()

    def test_secure_transfer_page_requires_auth(self):
        app = WebApp()
        _, resp = self._get(app, "/secure-transfer")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login"

    def test_secure_transfer_page_shows_token(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._get(app, "/secure-transfer", {"session_id": sid})
        assert resp.status_code == 200
        token = _csrf_token_for_session(sid)
        assert token in resp.body
        assert resp.headers["X-Sim-CSRF-Token"] == token
        assert resp.headers["X-Sim-CSRF-Kind"] == "token_shown"

    def test_transfer_requires_auth(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/transfer")
        req = build_request("POST", url, body="recipient=training-user&amount=100")
        resp = app.handle(req)
        assert resp.status_code == 401
        assert resp.headers["X-Sim-CSRF-Kind"] == "unauthenticated"

    def test_transfer_vulnerable_succeeds_with_cookie_only(self):
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/transfer")
        req = build_request("POST", url, body="recipient=training-user&amount=100",
                            cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-CSRF-Kind"] == "vulnerable_success"
        assert app.balances["student"] == 4900
        assert app.balances["training-user"] == 100

    def test_transfer_vulnerable_accepts_forged_origin(self):
        """The whole point of the mission: the vulnerable endpoint never
        inspects Origin/Referer at all — only the session cookie."""
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/transfer")
        req = build_request("POST", url, body="recipient=training-user&amount=100",
                            cookies={"session_id": sid},
                            extra_headers={"Origin": ATTACKER_ORIGIN, "Referer": f"{ATTACKER_ORIGIN}/"})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-CSRF-Kind"] == "attack_simulated"
        assert app.balances["training-user"] == 100

    def test_transfer_invalid_amount_rejected(self):
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/transfer")
        req = build_request("POST", url, body="recipient=training-user&amount=999999",
                            cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 400
        assert resp.headers["X-Sim-CSRF-Kind"] == "invalid_amount"

    def test_secure_transfer_missing_token_rejected(self):
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/secure-transfer")
        req = build_request("POST", url, body="recipient=training-user&amount=100",
                            cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 403
        assert resp.headers["X-Sim-CSRF-Kind"] == "missing_token"
        assert app.balances.get("training-user", 0) == 0

    def test_secure_transfer_invalid_token_rejected(self):
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/secure-transfer")
        req = build_request("POST", url,
                            body="recipient=training-user&amount=100&csrf_token=INVALID_TRAINING_TOKEN",
                            cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 403
        assert resp.headers["X-Sim-CSRF-Kind"] == "invalid_token"

    def test_secure_transfer_valid_token_accepted(self):
        app = WebApp()
        sid = self._login(app)
        token = _csrf_token_for_session(sid)
        url = parse_url(f"https://{HOST}/secure-transfer")
        req = build_request("POST", url,
                            body=f"recipient=training-user&amount=100&csrf_token={token}",
                            cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-CSRF-Kind"] == "token_valid"
        assert app.balances["training-user"] == 100

    def test_secure_transfer_unexpected_origin_rejected_even_with_valid_token(self):
        app = WebApp()
        sid = self._login(app)
        token = _csrf_token_for_session(sid)
        url = parse_url(f"https://{HOST}/secure-transfer")
        req = build_request("POST", url,
                            body=f"recipient=training-user&amount=100&csrf_token={token}",
                            cookies={"session_id": sid},
                            extra_headers={"Origin": ATTACKER_ORIGIN})
        resp = app.handle(req)
        assert resp.status_code == 403
        assert resp.headers["X-Sim-CSRF-Kind"] == "origin_rejected"
        assert app.balances.get("training-user", 0) == 0

    def test_secure_transfer_trusted_origin_allowed(self):
        app = WebApp()
        sid = self._login(app)
        token = _csrf_token_for_session(sid)
        url = parse_url(f"https://{HOST}/secure-transfer")
        req = build_request("POST", url,
                            body=f"recipient=training-user&amount=100&csrf_token={token}",
                            cookies={"session_id": sid},
                            extra_headers={"Origin": TRUSTED_ORIGIN})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-CSRF-Kind"] == "token_valid"

    def test_secure_transfer_no_origin_header_not_blocked(self):
        """Origin is absent on many real requests — the check must only
        ever reject an explicit, unexpected value, never absence."""
        app = WebApp()
        sid = self._login(app)
        token = _csrf_token_for_session(sid)
        url = parse_url(f"https://{HOST}/secure-transfer")
        req = build_request("POST", url,
                            body=f"recipient=training-user&amount=100&csrf_token={token}",
                            cookies={"session_id": sid})
        assert "Origin" not in req.headers
        resp = app.handle(req)
        assert resp.status_code == 200

    def test_transfer_get_route_does_not_exist(self):
        """No GET /transfer route at all (YC-035.6 GET-vs-POST objective)."""
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/transfer")
        req = build_request("GET", url, cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 404

    def test_transfer_history_shows_only_own_transfers(self):
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/transfer")
        req = build_request("POST", url, body="recipient=training-user&amount=100",
                            cookies={"session_id": sid})
        app.handle(req)
        _, resp = self._get(app, "/transfer-history", {"session_id": sid})
        assert resp.status_code == 200
        assert "training-user" in resp.body

    def test_csrf_token_deterministic_and_session_bound(self):
        assert _csrf_token_for_session("student-session") == _csrf_token_for_session("student-session")
        assert _csrf_token_for_session("student-session") != _csrf_token_for_session("admin-session")


# ═══════════════════════════════════════════
# CSRF state tracking (_track_csrf_response via open/forward/repeater)
# ═══════════════════════════════════════════
class TestCsrfStateTracking:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.web_lab = build_web_lab("csrf-investigation")
        return sh

    def _login(self, sh):
        sh.execute('open -X POST -d "username=student&password=training123" '
                  "https://cybershop.training/auth/login")

    def test_attack_simulated_flag(self):
        sh = self._shell()
        self._login(sh)
        sh.execute('open -X POST -H "Origin: https://attacker.training" '
                  '-d "recipient=training-user&amount=100" https://cybershop.training/transfer')
        assert sh.web_lab.csrf.attack_simulated is True

    def test_token_viewed_flag(self):
        sh = self._shell()
        self._login(sh)
        assert sh.web_lab.csrf.token_viewed is False
        sh.execute("open https://cybershop.training/secure-transfer")
        assert sh.web_lab.csrf.token_viewed is True

    def test_missing_and_invalid_and_valid_token_flags(self):
        sh = self._shell()
        self._login(sh)
        sh.execute('open -X POST -d "recipient=training-user&amount=100" '
                  "https://cybershop.training/secure-transfer")
        assert sh.web_lab.csrf.missing_token_rejected is True
        sh.execute('open -X POST -d "recipient=training-user&amount=100&csrf_token=BAD" '
                  "https://cybershop.training/secure-transfer")
        assert sh.web_lab.csrf.invalid_token_rejected is True
        token = _csrf_token_for_session(STUDENT_SID)
        sh.execute(f'open -X POST -d "recipient=training-user&amount=100&csrf_token={token}" '
                  "https://cybershop.training/secure-transfer")
        assert sh.web_lab.csrf.valid_token_accepted is True

    def test_origin_rejected_flag_via_forward(self):
        sh = self._shell()
        self._login(sh)
        token = _csrf_token_for_session(STUDENT_SID)
        sh.execute("intercept on")
        sh.execute(f'open -X POST -H "Origin: https://attacker.training" '
                  f'-d "recipient=training-user&amount=100&csrf_token={token}" '
                  "https://cybershop.training/secure-transfer")
        assert sh.web_lab.csrf.origin_rejected is False  # queued, not yet handled
        sh.execute("forward")
        assert sh.web_lab.csrf.origin_rejected is True

    def test_valid_token_flag_via_repeater_send(self):
        sh = self._shell()
        self._login(sh)
        sh.execute('open -X POST -d "recipient=training-user&amount=1&csrf_token=x" '
                  "https://cybershop.training/secure-transfer")
        sh.execute("repeater 2")
        token = _csrf_token_for_session(STUDENT_SID)
        sh.execute(f'edit body "recipient=training-user&amount=100&csrf_token={token}"')
        assert sh.web_lab.csrf.valid_token_accepted is False
        sh.execute("repeater send")
        assert sh.web_lab.csrf.valid_token_accepted is True

    def test_samesite_command_increments_counter(self):
        sh = self._shell()
        assert sh.web_lab.csrf.samesite_inspected == 0
        out = sh.execute("samesite strict")
        assert "Strict" in out
        assert sh.web_lab.csrf.samesite_inspected == 1
        sh.execute("samesite lax")
        sh.execute("samesite none")
        assert sh.web_lab.csrf.samesite_inspected == 3

    def test_samesite_none_would_attach_cookie(self):
        sh = self._shell()
        out = sh.execute("samesite none")
        assert "would attach the cookie: yes" in out.lower()

    def test_samesite_strict_and_lax_would_not_attach_cookie(self):
        sh = self._shell()
        for policy in ("strict", "lax"):
            out = sh.execute(f"samesite {policy}")
            assert "would attach the cookie: no" in out.lower()

    def test_samesite_invalid_policy(self):
        sh = self._shell()
        out = sh.execute("samesite bogus")
        assert "Usage" in out
        assert sh.web_lab.csrf.samesite_inspected == 0

    def test_state_survives_save_and_restore(self):
        sh = self._shell()
        self._login(sh)
        sh.execute('open -X POST -H "Origin: https://attacker.training" '
                  '-d "recipient=training-user&amount=100" https://cybershop.training/transfer')
        snapshot = sh.web_lab.to_dict()
        lab2 = build_web_lab("csrf-investigation")
        lab2.apply_state(snapshot)
        assert lab2.csrf.attack_simulated is True
        assert lab2.app.balances["training-user"] == 100

    def test_transfers_persist_through_save_and_restore(self):
        sh = self._shell()
        self._login(sh)
        sh.execute('open -X POST -d "recipient=training-user&amount=42" '
                  "https://cybershop.training/transfer")
        snapshot = sh.web_lab.to_dict()
        lab2 = build_web_lab("csrf-investigation")
        lab2.apply_state(snapshot)
        assert len(lab2.app.transfers) == 1
        assert lab2.app.transfers[0].amount == 42


# ═══════════════════════════════════════════
# Validator — new checks
# ═══════════════════════════════════════════
class TestCsrfValidatorChecks:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab("csrf-investigation")
        return sh

    def _login(self, sh):
        sh.execute('open -X POST -d "username=student&password=training123" '
                  "https://cybershop.training/auth/login")

    def _obj(self, check, match="1", **extra):
        v = {"type": "web_state", "check": check, "match": match}
        v.update(extra)
        return {"id": "c", "xp": 10, "validate": v}

    def test_state_change_identified(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("state_change_identified")
        assert not validate(obj, sh).passed
        sh.execute('open -X POST -d "recipient=training-user&amount=10" '
                  "https://cybershop.training/transfer")
        assert validate(obj, sh).passed

    def test_get_vs_post_identified(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("get_vs_post_identified")
        assert not validate(obj, sh).passed
        sh.execute("open https://cybershop.training/transfer")
        assert validate(obj, sh).passed

    def test_csrf_simulated(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("csrf_simulated")
        assert not validate(obj, sh).passed
        sh.execute('open -X POST -H "Origin: https://attacker.training" '
                  '-d "recipient=training-user&amount=100" https://cybershop.training/transfer')
        assert validate(obj, sh).passed

    def test_csrf_token_identified(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("csrf_token_identified")
        assert not validate(obj, sh).passed
        sh.execute("open https://cybershop.training/secure-transfer")
        assert validate(obj, sh).passed

    def test_missing_token_rejected(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("missing_token_rejected")
        assert not validate(obj, sh).passed
        sh.execute('open -X POST -d "recipient=training-user&amount=100" '
                  "https://cybershop.training/secure-transfer")
        assert validate(obj, sh).passed

    def test_invalid_token_rejected(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("invalid_token_rejected")
        assert not validate(obj, sh).passed
        sh.execute('open -X POST -d "recipient=training-user&amount=100&csrf_token=WRONG" '
                  "https://cybershop.training/secure-transfer")
        assert validate(obj, sh).passed

    def test_valid_token_accepted(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("valid_token_accepted")
        token = _csrf_token_for_session(STUDENT_SID)
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -d "recipient=training-user&amount=100&csrf_token={token}" '
                  "https://cybershop.training/secure-transfer")
        assert validate(obj, sh).passed

    def test_origin_rejected(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("origin_rejected")
        assert not validate(obj, sh).passed
        sh.execute('open -X POST -H "Origin: https://attacker.training" '
                  '-d "recipient=training-user&amount=100" https://cybershop.training/secure-transfer')
        assert validate(obj, sh).passed

    def test_samesite_inspected_requires_three(self):
        sh = self._shell()
        obj = self._obj("samesite_inspected", match="3")
        sh.execute("samesite strict")
        sh.execute("samesite lax")
        assert not validate(obj, sh).passed
        sh.execute("samesite none")
        assert validate(obj, sh).passed

    def test_csrf_evidence_collected(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("csrf_evidence_collected")
        token = _csrf_token_for_session(STUDENT_SID)
        sh.execute('open -X POST -H "Origin: https://attacker.training" '
                  '-d "recipient=training-user&amount=10" https://cybershop.training/transfer')
        sh.execute("open https://cybershop.training/secure-transfer")
        sh.execute('open -X POST -d "recipient=training-user&amount=10" '
                  "https://cybershop.training/secure-transfer")
        sh.execute('open -X POST -d "recipient=training-user&amount=10&csrf_token=WRONG" '
                  "https://cybershop.training/secure-transfer")
        sh.execute(f'open -X POST -d "recipient=training-user&amount=10&csrf_token={token}" '
                  "https://cybershop.training/secure-transfer")
        assert not validate(obj, sh).passed  # origin_rejected still missing
        sh.execute('open -X POST -H "Origin: https://attacker.training" '
                  '-d "recipient=training-user&amount=10" https://cybershop.training/secure-transfer')
        assert validate(obj, sh).passed

    def test_checks_fail_gracefully_without_web_lab(self):
        sh = Shell()
        for check in ("state_change_identified", "get_vs_post_identified", "csrf_simulated",
                      "csrf_token_identified", "missing_token_rejected", "invalid_token_rejected",
                      "valid_token_accepted", "origin_rejected", "samesite_inspected",
                      "csrf_evidence_collected"):
            assert not validate(self._obj(check), sh).passed

    def test_csrf_evidence_collected_does_not_reuse_other_missions_evidence_checks(self):
        """Guards against capstone checks colliding across missions —
        each mission's own name reads its own WebLab sub-state."""
        sh = self._shell()
        self._login(sh)
        sh.execute('open -X POST -d "recipient=training-user&amount=10" '
                  "https://cybershop.training/transfer")
        assert not validate(self._obj("evidence_collected"), sh).passed  # SQLi's name
        assert not validate(self._obj("xss_evidence_collected"), sh).passed  # XSS's name


# ═══════════════════════════════════════════
# Investigation scenario
# ═══════════════════════════════════════════
class TestInvestigationScenario:
    def test_csrf_investigation_scenario(self):
        lab = build_web_lab("csrf-investigation")
        assert len(lab.investigation_log) == 5

        login_req, login_resp = lab.investigation_log[0]
        assert login_req.path == "/auth/login"
        assert login_resp.status_code == 302

        legit_req, legit_resp = lab.investigation_log[1]
        assert legit_req.path == "/transfer"
        assert legit_resp.headers["X-Sim-CSRF-Kind"] == "vulnerable_success"

        forged_req, forged_resp = lab.investigation_log[2]
        assert forged_req.path == "/transfer"
        assert forged_req.headers.get("Origin") == ATTACKER_ORIGIN
        assert forged_resp.status_code == 200
        assert forged_resp.headers["X-Sim-CSRF-Kind"] == "attack_simulated"

        secure_no_token_req, secure_no_token_resp = lab.investigation_log[3]
        assert secure_no_token_req.path == "/secure-transfer"
        assert secure_no_token_resp.status_code == 403

        secure_valid_req, secure_valid_resp = lab.investigation_log[4]
        assert secure_valid_req.path == "/secure-transfer"
        assert secure_valid_resp.status_code == 200
        assert secure_valid_resp.headers["X-Sim-CSRF-Kind"] == "token_valid"

    def test_scenario_is_deterministic(self):
        a = build_web_lab("csrf-investigation")
        b = build_web_lab("csrf-investigation")
        assert a.investigation_log == b.investigation_log

    def test_scenario_never_touches_live_session(self):
        lab = build_web_lab("csrf-investigation")
        assert lab.session.history == []
        assert lab.session.cookies == {}
        assert lab.csrf.attack_simulated is False
        assert lab.app.transfers == []


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "csrf-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("csrf-fundamentals")
        assert m is not None
        assert m["title"] == "Cross-Site Request Forgery Fundamentals"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 750

    def test_objective_count(self):
        m = get_mission("csrf-fundamentals")
        assert len(m["objectives"]) == 17

    def test_xp_sums_to_total(self):
        m = get_mission("csrf-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_every_objective_has_progressive_hints(self):
        m = get_mission("csrf-fundamentals")
        for o in m["objectives"]:
            assert "hints" in o
            assert len(o["hints"]) >= 2

    def test_chained_after_xss_fundamentals(self):
        assert MISSIONS["xss-fundamentals"]["next_mission"] == "csrf-fundamentals"

    def test_chains_to_file_upload_security(self):
        m = get_mission("csrf-fundamentals")
        assert m["next_mission"] == "file-upload-security"

    def test_web_lab_scenario_set(self):
        m = get_mission("csrf-fundamentals")
        assert m["web_lab"] == "csrf-investigation"

    def test_web_workspace_seeded(self):
        m = get_mission("csrf-fundamentals")
        assert "web" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("csrf-fundamentals", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 750
        assert sorted(r.progress.completed_ids) == sorted(
            o["id"] for o in r.mission["objectives"])

    def test_no_premature_completion(self):
        r = MissionRunner("csrf-fundamentals", 2)
        r.execute("web")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) < len(r.mission["objectives"])

    def test_web_lab_status_carries_csrf_fields_and_transfers(self):
        r = MissionRunner("csrf-fundamentals", 3)
        r.execute('open -X POST -d "username=student&password=training123" '
                 "https://cybershop.training/auth/login")
        r.execute('open -X POST -H "Origin: https://attacker.training" '
                 '-d "recipient=training-user&amount=100" https://cybershop.training/transfer')
        status = r.web_lab_status()
        assert status["csrf"]["attack_simulated"] is True
        assert len(status["transfers"]) == 1
        assert status["transfers"][0]["amount"] == 100
        assert status["balances"]["student"] == 4900

    def test_ai_context_includes_csrf_summary(self):
        r = MissionRunner("csrf-fundamentals", 4)
        r.execute('open -X POST -d "username=student&password=training123" '
                 "https://cybershop.training/auth/login")
        r.execute("open https://cybershop.training/secure-transfer")
        ctx = r.ai_context()
        assert ctx["web"]["csrf"]["token_viewed"] is True
        assert ctx["web"]["csrf"]["attack_simulated"] is False
        assert ctx["web"]["csrf"]["last_csrf_kind"] == "token_shown"

    def test_save_restore_preserves_csrf_state(self):
        r = MissionRunner("csrf-fundamentals", 5)
        r.execute('open -X POST -d "username=student&password=training123" '
                 "https://cybershop.training/auth/login")
        r.execute("samesite strict")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.shell.web_lab.csrf.samesite_inspected == 1

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("csrf-fundamentals", 6)
        r1.execute('open -X POST -d "username=student&password=training123" '
                  "https://cybershop.training/auth/login")
        r1.execute("open https://cybershop.training/secure-transfer")
        assert MissionRunner("csrf-fundamentals", 7).shell.web_lab.csrf.token_viewed is False


# ═══════════════════════════════════════════
# Security isolation
# ═══════════════════════════════════════════
class TestSecurityIsolation:
    def test_web_module_still_has_no_network_or_db_imports(self):
        import ast

        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        forbidden = {"socket", "subprocess", "requests", "http.client", "os",
                    "urllib.request", "shutil", "ftplib", "smtplib",
                    "sqlite3", "psycopg2", "pymysql", "mysql", "sqlalchemy"}
        assert not (imported_modules & forbidden), \
            f"forbidden imports: {imported_modules & forbidden}"

    def test_commands_module_has_no_network_or_db_imports(self):
        import ast

        import app.core.terminal.commands as cmdmod
        with open(cmdmod.__file__, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        forbidden = {"socket", "subprocess", "requests", "http.client",
                    "urllib.request", "sqlite3", "psycopg2", "pymysql"}
        assert not (imported_modules & forbidden), \
            f"forbidden imports: {imported_modules & forbidden}"

    def test_new_routes_reject_external_host(self):
        sh = Shell()
        sh.web_lab = build_web_lab("csrf-investigation")
        for path in ("/csrf-demo", "/secure-transfer", "/transfer-history"):
            out = sh.execute(f"open https://evil.example.com{path}")
            assert out == "External hosts are not available in the training environment."

    def test_attacker_origin_never_reaches_a_second_host(self):
        """'attacker.training' only ever appears as a header *value* on a
        request whose host is still the one simulated site — this module
        has no concept of a second host to actually contact."""
        app = WebApp()
        url = parse_url(f"https://{HOST}/transfer")
        req = build_request("POST", url, body="recipient=training-user&amount=1",
                            extra_headers={"Origin": ATTACKER_ORIGIN})
        assert req.host == HOST
        resp = app.handle(req)
        assert resp.status_code == 401  # not logged in — still routed to the one simulated app

    def test_no_eval_or_dangerous_apis_in_module(self):
        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read()
        for dangerous in ("eval(", "exec(", "compile(", "__import__", "subprocess."):
            assert dangerous not in src

    def test_no_eval_or_dangerous_dom_apis_in_terminal_js_csrf_section(self):
        js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static",
                               "labs", "terminal.js")
        with open(js_path, encoding="utf-8") as f:
            js = f.read()
        start = js.index("CSRF Fundamentals (YC-035.6)")
        section = js[start:start + 12000]
        for dangerous in ("eval(", "document.write", "Function(", "fetch(", "XMLHttpRequest"):
            assert dangerous not in section

    def test_no_real_credentials_or_secrets_anywhere_in_module(self):
        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read().lower()
        for weak in ("password123", "letmein", "qwerty", "admin@yushacyber.com"):
            assert weak not in src

    def test_csrf_state_isolated_between_instances(self):
        lab1 = build_web_lab("csrf-investigation")
        lab2 = build_web_lab("csrf-investigation")
        url = parse_url(f"https://{HOST}/secure-transfer")
        lab1.app.handle(build_request("GET", url))
        assert lab1.csrf.token_viewed is False  # app.handle() alone never mutates lab.csrf
        assert lab2.csrf.token_viewed is False

    def test_balances_isolated_between_instances(self):
        lab1 = build_web_lab("csrf-investigation")
        lab2 = build_web_lab("csrf-investigation")
        url = parse_url(f"https://{HOST}/auth/login")
        resp = lab1.app.handle(build_request("POST", url, body="username=student&password=training123"))
        sid = resp.cookies["session_id"]
        url = parse_url(f"https://{HOST}/transfer")
        lab1.app.handle(build_request("POST", url, body="recipient=training-user&amount=500",
                                      cookies={"session_id": sid}))
        assert lab1.app.balances["student"] == 4500
        assert lab2.app.balances.get("student", 5000) == 5000


# ═══════════════════════════════════════════
# Services — full chain unlock/completion with real XP
# ═══════════════════════════════════════════
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    a = create_app()
    a.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with a.app_context():
        db.create_all()
    yield a


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        u = User(username="csrf_test", email="csrf@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "csrf_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


XSS_SOLVE_MARKER = "<TRAINING_XSS>"
XSS_SOLVE: list[str] = [
    "web",
    "open https://cybershop.training/search?q=laptop",
    f'open "https://cybershop.training/search?q={XSS_SOLVE_MARKER}"',
    "intercept on",
    "open https://cybershop.training/search?q=keyboard",
    "forward",
    "intercept off",
    f'open -X POST -d "name=student&comment={XSS_SOLVE_MARKER}" https://cybershop.training/feedback',
    "open https://cybershop.training/comments",
    "open https://cybershop.training/dom-demo",
    f'open "https://cybershop.training/dom-demo?input={XSS_SOLVE_MARKER}"',
    f'open "https://cybershop.training/secure-search?q={XSS_SOLVE_MARKER}"',
    "evidence",
    "inspect 1", "inspect 2", "inspect 3", "inspect 4", "inspect 5",
    ('echo "Conclusion: the search and comments endpoints reflect and store the '
     "training marker unsafely as HTML - reflected and stored XSS. The secure "
     "endpoint shows the same marker safely HTML-escaped, proving output encoding "
     'is the correct defensive control." > web/xss-investigation.txt'),
]


class TestServices:
    def test_full_chain_unlocks_and_completes_with_real_xp(self, app, student):
        _uname, uid = student
        with app.app_context():
            from app.auth.models import User
            from app.core.missions import (
                dashboard_stats,
                execute_command,
                mission_status,
                start_mission,
            )

            assert mission_status(uid, "csrf-fundamentals") == "locked"

            start_mission(uid, "xss-fundamentals")
            for c in XSS_SOLVE:
                execute_command(uid, "xss-fundamentals", c)

            assert mission_status(uid, "csrf-fundamentals") == "available"

            start_mission(uid, "csrf-fundamentals")
            for c in SOLVE:
                execute_command(uid, "csrf-fundamentals", c)

            assert mission_status(uid, "csrf-fundamentals") == "completed"

            user = User.query.get(uid)
            assert user.xp > 0
            assert user.level >= 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] >= 2


# ═══════════════════════════════════════════
# HTTP — pages / UI reachability
# ═══════════════════════════════════════════
class TestHTTP:
    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "csrf-fundamentals" in ids

    def test_terminal_page_shows_csrf_panels(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/csrf-fundamentals")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "data-csrf-badges" in body
            assert "data-csrf-transfer-vuln" in body
            assert "data-csrf-secure-send" in body
            assert "data-csrf-attacker-simulate" in body
            assert "data-csrf-samesite" in body
            assert "data-csrf-origin-send" in body
            assert "data-csrf-flow-step" in body
            assert "data-csrf-get-attempt" in body
            # Proxy Control (reused from YC-035.2) also present for this mission.
            assert "data-proxy-badge" in body
            # Inspector (reused from YC-035.1) still present too.
            assert "data-inspector-toggle" in body

    def test_csrf_panel_not_shown_on_other_missions(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/xss-fundamentals")
            assert "data-csrf-badges" not in r.data.decode("utf-8")
            r2 = c.get("/terminal/mission/sql-injection-fundamentals")
            assert "data-csrf-badges" not in r2.data.decode("utf-8")

    def test_execute_returns_csrf_state(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/csrf-fundamentals")
            c.post("/api/terminal/mission/execute", json={
                "slug": "csrf-fundamentals",
                "command": 'open -X POST -d "username=student&password=training123" '
                           "https://cybershop.training/auth/login",
            })
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "csrf-fundamentals",
                "command": "open https://cybershop.training/secure-transfer",
            })
            assert r.status_code == 200
            d = r.get_json()
            assert d["web_lab_status"]["csrf"]["token_viewed"] is True

    def test_hint_endpoint_returns_progressive_hints(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/csrf-fundamentals")
            r1 = c.post("/api/terminal/mission/hint", json={
                "slug": "csrf-fundamentals", "objective_id": "cs-1"})
            r2 = c.post("/api/terminal/mission/hint", json={
                "slug": "csrf-fundamentals", "objective_id": "cs-1"})
            assert r1.status_code == 200 and r2.status_code == 200
            assert r1.get_json()["hint"] != r2.get_json()["hint"]
