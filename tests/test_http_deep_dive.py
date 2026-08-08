"""Tests for YC-035.1 — HTTP Deep Dive interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0351-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_hd.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell
from app.core.terminal.web import (
    API_TOKEN,
    HOST,
    build_request,
    build_web_lab,
    parse_body,
    parse_url,
)

SOLVE: list[str] = [
    "open https://cybershop.training/products",
    "headers",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login',
    'open -X POST -H "Content-Type: application/json" -d \'{"bio": "training"}\' https://cybershop.training/api/profile',
    "open https://cybershop.training/search?q=web%20security",
    "open https://cybershop.training/login",
    'open -H "Authorization: Bearer training-token-001" https://cybershop.training/api/me',
    'open -H "Referer: https://cybershop.training/" https://cybershop.training/products',
    "open https://cybershop.training/products?id=42",
    "open https://cybershop.training/login",
    "open https://cybershop.training/auth/login",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login',
    "evidence", "inspect 1", "inspect 2", "inspect 3", "inspect 4",
    ('echo "Conclusion: the profile response Content-Type is application/json '
     'instead of text/html" > web/http-investigation.txt'),
]


# ═══════════════════════════════════════════
# Request/response model — JSON bodies, extra headers
# ═══════════════════════════════════════════
class TestRequestResponseModel:
    def test_extra_headers_override_defaults(self):
        url = parse_url(f"https://{HOST}/api/me")
        req = build_request("GET", url, extra_headers={"Authorization": "Bearer training-token-001"})
        assert req.headers["Authorization"] == "Bearer training-token-001"
        # Defaults are still present.
        assert req.headers["Host"] == HOST

    def test_extra_headers_can_override_content_type(self):
        url = parse_url(f"https://{HOST}/api/profile")
        req = build_request("POST", url, body='{"bio": "x"}',
                            extra_headers={"Content-Type": "application/json"})
        assert req.headers["Content-Type"] == "application/json"
        assert req.headers["Content-Length"] == str(len('{"bio": "x"}'))

    def test_body_defaults_to_form_encoded_without_override(self):
        url = parse_url(f"https://{HOST}/auth/login")
        req = build_request("POST", url, body="username=student&password=training123")
        assert req.headers["Content-Type"] == "application/x-www-form-urlencoded"


class TestParseBody:
    def test_parses_json(self):
        assert parse_body('{"a": "b"}', "application/json") == {"a": "b"}

    def test_parses_form(self):
        assert parse_body("a=b&c=d", "application/x-www-form-urlencoded") == {"a": "b", "c": "d"}

    def test_malformed_json_returns_empty(self):
        assert parse_body("{not json", "application/json") == {}

    def test_empty_body_returns_empty(self):
        assert parse_body("", "application/json") == {}

    def test_non_dict_json_returns_empty(self):
        assert parse_body("[1, 2, 3]", "application/json") == {}


# ═══════════════════════════════════════════
# WebApp routing — new routes
# ═══════════════════════════════════════════
class TestWebAppRouting:
    def _app(self):
        from app.core.terminal.web import WebApp
        return WebApp()

    def test_auth_login_post_alias_works(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/auth/login")
        req = build_request("POST", url, body="username=student&password=training123")
        resp = app.handle(req)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/profile"
        assert resp.cookies["session_id"] == "student-session"

    def test_api_login_success(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/api/login")
        req = build_request("POST", url, body='{"username": "student", "password": "training123"}',
                            extra_headers={"Content-Type": "application/json"})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert resp.content_type == "application/json"
        assert '"status": "success"' in resp.body

    def test_api_login_failure(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/api/login")
        req = build_request("POST", url, body='{"username": "student", "password": "wrong"}',
                            extra_headers={"Content-Type": "application/json"})
        resp = app.handle(req)
        assert resp.status_code == 401
        assert '"status": "error"' in resp.body

    def test_api_profile_requires_session_cookie(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/api/profile")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert resp.status_code == 401

    def test_api_profile_get_with_session(self):
        app = self._app()
        login_url = parse_url(f"https://{HOST}/auth/login")
        login_req = build_request("POST", login_url, body="username=student&password=training123")
        login_resp = app.handle(login_req)
        sid = login_resp.cookies["session_id"]

        url = parse_url(f"https://{HOST}/api/profile")
        req = build_request("GET", url, cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert '"username": "student"' in resp.body

    def test_api_profile_post_updates(self):
        app = self._app()
        login_url = parse_url(f"https://{HOST}/auth/login")
        login_req = build_request("POST", login_url, body="username=student&password=training123")
        sid = app.handle(login_req).cookies["session_id"]

        url = parse_url(f"https://{HOST}/api/profile")
        req = build_request("POST", url, body='{"bio": "x"}', cookies={"session_id": sid},
                            extra_headers={"Content-Type": "application/json"})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert '"status": "updated"' in resp.body

    def test_api_me_requires_bearer_token(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/api/me")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert resp.status_code == 401

    def test_api_me_with_valid_token(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/api/me")
        req = build_request("GET", url, extra_headers={"Authorization": f"Bearer {API_TOKEN}"})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert '"username": "student"' in resp.body

    def test_api_me_rejects_session_cookie_only(self):
        # /api/me is bearer-token-only by design — a session cookie alone
        # must not satisfy it (kept as a conceptually separate mechanism).
        app = self._app()
        login_url = parse_url(f"https://{HOST}/auth/login")
        login_req = build_request("POST", login_url, body="username=student&password=training123")
        sid = app.handle(login_req).cookies["session_id"]

        url = parse_url(f"https://{HOST}/api/me")
        req = build_request("GET", url, cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 401

    def test_api_me_wrong_token_rejected(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/api/me")
        req = build_request("GET", url, extra_headers={"Authorization": "Bearer wrong-token"})
        resp = app.handle(req)
        assert resp.status_code == 401

    def test_products_with_id_has_cache_headers(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/products?id=42")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert resp.headers["Cache-Control"] == "max-age=60"
        assert resp.headers["ETag"] == '"product-42-v1"'
        assert "Last-Modified" in resp.headers

    def test_products_without_id_has_no_cache_headers(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/products")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert "Cache-Control" not in resp.headers or resp.headers["Cache-Control"] != "max-age=60"

    def test_unknown_api_route_404(self):
        app = self._app()
        url = parse_url(f"https://{HOST}/api/does-not-exist")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert resp.status_code == 404

    def test_url_encoded_query_decodes(self):
        u = parse_url("https://cybershop.training/search?q=web%20security")
        assert u.query["q"] == "web security"


# ═══════════════════════════════════════════
# open command: -H flag
# ═══════════════════════════════════════════
class TestOpenHeaderFlag:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab()
        return sh

    def test_dash_h_sets_header(self):
        sh = self._shell()
        sh.execute('open -H "Referer: https://cybershop.training/" https://cybershop.training/products')
        assert sh.web_lab.session.last_request.headers["Referer"] == "https://cybershop.training/"

    def test_dash_h_repeatable(self):
        sh = self._shell()
        sh.execute('open -H "Referer: https://cybershop.training/" '
                  '-H "Authorization: Bearer training-token-001" '
                  'https://cybershop.training/api/me')
        req = sh.web_lab.session.last_request
        assert req.headers["Referer"] == "https://cybershop.training/"
        assert req.headers["Authorization"] == "Bearer training-token-001"

    def test_dash_h_can_set_json_content_type(self):
        sh = self._shell()
        sh.execute('open -X POST -H "Content-Type: application/json" -d \'{"bio": "x"}\' '
                  'https://cybershop.training/api/profile')
        assert sh.web_lab.session.last_request.headers["Content-Type"] == "application/json"

    def test_requests_command_lists_history(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products")
        sh.execute("open https://cybershop.training/")
        out = sh.execute("requests")
        assert "#1  GET /products" in out
        assert "#2  GET /" in out

    def test_requests_command_empty(self):
        sh = self._shell()
        assert "No requests made yet" in sh.execute("requests")


# ═══════════════════════════════════════════
# Validator — body_field, history_sequence, request_count
# ═══════════════════════════════════════════
class TestNewValidatorChecks:
    def _shell(self, scenario="login-flow"):
        sh = Shell()
        sh.web_lab = build_web_lab(scenario)
        return sh

    def test_body_field_request(self):
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/auth/login')
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "web_state", "check": "body_field", "in": "request",
            "field": "username", "match": "student"}}
        assert validate(obj, sh).passed

    def test_body_field_response(self):
        sh = self._shell()
        sh.execute('open -H "Authorization: Bearer training-token-001" '
                  'https://cybershop.training/api/me')
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "web_state", "check": "body_field", "in": "response",
            "field": "username", "match": "student"}}
        assert validate(obj, sh).passed

    def test_body_field_fails_without_request(self):
        sh = self._shell()
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "web_state", "check": "body_field", "in": "response",
            "field": "username", "match": "student"}}
        assert not validate(obj, sh).passed

    def test_history_sequence_passes_in_order(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/login")
        sh.execute("open https://cybershop.training/auth/login")
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/auth/login')
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "web_state", "check": "history_sequence",
            "match": ["GET /login", "GET /auth/login", "POST /auth/login"]}}
        assert validate(obj, sh).passed

    def test_history_sequence_fails_out_of_order(self):
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/auth/login')
        sh.execute("open https://cybershop.training/login")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "web_state", "check": "history_sequence",
            "match": ["GET /login", "GET /auth/login", "POST /auth/login"]}}
        assert not validate(obj, sh).passed

    def test_history_sequence_does_not_prematurely_pass_on_partial_evidence(self):
        # An early, coincidental POST /auth/login before GET /login was
        # ever made must not count toward the sequence (regression guard
        # for the exact NameError/logic bug caught during development).
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/auth/login')  # too early
        sh.execute("open https://cybershop.training/products")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "web_state", "check": "history_sequence",
            "match": ["GET /login", "GET /auth/login", "POST /auth/login"]}}
        assert not validate(obj, sh).passed

    def test_request_count(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products")
        sh.execute("open https://cybershop.training/")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "web_state", "check": "request_count", "match": "2"}}
        assert validate(obj, sh).passed
        obj2 = {"id": "x", "xp": 10, "validate": {
            "type": "web_state", "check": "request_count", "match": "5"}}
        assert not validate(obj2, sh).passed


# ═══════════════════════════════════════════
# Investigation scenarios / web lab scenario registry
# ═══════════════════════════════════════════
class TestInvestigationScenarios:
    def test_default_scenario_is_login_flow(self):
        lab = build_web_lab()
        assert len(lab.investigation_log) == 3

    def test_content_type_bug_scenario(self):
        lab = build_web_lab("content-type-bug")
        assert len(lab.investigation_log) == 4
        last_req, last_resp = lab.investigation_log[-1]
        assert last_req.method == "GET"
        assert last_req.path == "/profile"
        assert last_resp.status_code == 200
        assert last_resp.headers["Content-Type"] == "application/json"

    def test_content_type_bug_scenario_is_deterministic(self):
        a = build_web_lab("content-type-bug")
        b = build_web_lab("content-type-bug")
        assert a.investigation_log == b.investigation_log

    def test_unknown_scenario_falls_back_to_default(self):
        lab = build_web_lab("not-a-real-scenario")
        assert len(lab.investigation_log) == 3


# ═══════════════════════════════════════════
# Progressive hints
# ═══════════════════════════════════════════
class TestProgressiveHints:
    def test_first_hint_is_conceptual_not_the_answer(self):
        r = MissionRunner("http-deep-dive", 1)
        hint = r.use_hint("hd-1")
        assert "open" not in hint.lower()

    def test_hints_escalate(self):
        r = MissionRunner("http-deep-dive", 2)
        h1 = r.use_hint("hd-1")
        h2 = r.use_hint("hd-1")
        h3 = r.use_hint("hd-1")
        assert h1 != h2 != h3
        assert "open https://cybershop.training/products" in h3

    def test_hints_cap_at_last_level(self):
        r = MissionRunner("http-deep-dive", 3)
        for _ in range(5):
            last = r.use_hint("hd-1")
        assert "open https://cybershop.training/products" in last

    def test_hints_used_counter_increments(self):
        r = MissionRunner("http-deep-dive", 4)
        r.use_hint("hd-1")
        r.use_hint("hd-2")
        assert r.progress.hints_used == 2

    def test_hint_progress_is_per_objective(self):
        r = MissionRunner("http-deep-dive", 5)
        r.use_hint("hd-1")
        r.use_hint("hd-1")
        first_hint_hd2 = r.use_hint("hd-2")
        assert r.progress.hint_index["hd-1"] == 2
        assert r.progress.hint_index["hd-2"] == 1
        assert first_hint_hd2 == r.mission["objectives"][1]["hints"][0]

    def test_legacy_single_hint_still_works(self):
        # web-fundamentals (YC-035.0) objectives still use a plain "hint"
        # string — must be entirely unaffected by this mission's change.
        r = MissionRunner("web-fundamentals", 6)
        hint = r.use_hint("wb-5")
        assert "does-not-exist" in hint


# ═══════════════════════════════════════════
# Security isolation
# ═══════════════════════════════════════════
class TestSecurityIsolation:
    def test_web_module_still_has_no_network_capable_imports(self):
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
                    "urllib.request", "shutil", "ftplib", "smtplib"}
        assert not (imported_modules & forbidden), \
            f"forbidden imports: {imported_modules & forbidden}"
        assert any(m == "urllib.parse" or m.startswith("urllib.parse")
                  for m in imported_modules)
        # json is pure serialization — no I/O, expected and fine.
        assert "json" in imported_modules

    def test_external_host_rejected_before_request_object_exists(self):
        sh = Shell()
        sh.web_lab = build_web_lab()
        out = sh.execute("open https://evil.example.com/")
        assert out == "External hosts are not available in the training environment."
        assert sh.web_lab.session.last_request is None

    def test_external_host_rejected_even_with_dash_h_flags(self):
        sh = Shell()
        sh.web_lab = build_web_lab()
        out = sh.execute('open -H "Authorization: Bearer x" https://evil.example.com/api/me')
        assert out == "External hosts are not available in the training environment."
        assert sh.web_lab.session.last_request is None

    def test_unknown_route_404_not_a_crash(self):
        sh = Shell()
        sh.web_lab = build_web_lab()
        out = sh.execute("open https://cybershop.training/does-not-exist-either")
        assert "404" in out

    def test_no_random_module_used(self):
        import ast

        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert "random" not in {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module != "random"


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "http-deep-dive" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("http-deep-dive")
        assert m is not None
        assert m["title"] == "HTTP Deep Dive"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 500

    def test_objective_count(self):
        m = get_mission("http-deep-dive")
        assert len(m["objectives"]) == 14

    def test_xp_sums_to_total(self):
        m = get_mission("http-deep-dive")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_every_objective_has_progressive_hints(self):
        m = get_mission("http-deep-dive")
        for o in m["objectives"]:
            assert "hints" in o
            assert len(o["hints"]) >= 2

    def test_chained_after_web_fundamentals(self):
        assert MISSIONS["web-fundamentals"]["next_mission"] == "http-deep-dive"

    def test_chained_before_burp_fundamentals(self):
        # No longer the terminal mission in the Web Security path — YC-035.2
        # (Burp Suite Fundamentals) now follows it.
        m = get_mission("http-deep-dive")
        assert m["next_mission"] == "burp-fundamentals"

    def test_web_lab_scenario_set(self):
        m = get_mission("http-deep-dive")
        assert m["web_lab"] == "content-type-bug"

    def test_web_workspace_seeded(self):
        m = get_mission("http-deep-dive")
        assert "web" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("http-deep-dive", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 500
        assert sorted(r.progress.completed_ids) == sorted(
            o["id"] for o in r.mission["objectives"])

    def test_no_premature_completion(self):
        r = MissionRunner("http-deep-dive", 2)
        r.execute("open https://cybershop.training/products?id=42")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) < len(r.mission["objectives"])

    def test_partial_progress_persists(self):
        r = MissionRunner("http-deep-dive", 3)
        r.execute("open https://cybershop.training/products")
        assert len(r.progress.completed_ids) >= 1

    def test_ai_context_includes_web_status(self):
        r = MissionRunner("http-deep-dive", 4)
        r.execute("open https://cybershop.training/products?id=42")
        ctx = r.ai_context()
        assert ctx["web"]["last_status"] == 200
        assert ctx["web"]["last_path"] == "/products"
        assert "ETag" in ctx["web"]["last_response_headers"]
        assert ctx["web"]["recent_history"] == ["GET /products -> 200"]

    def test_web_lab_status_carries_full_request_response(self):
        r = MissionRunner("http-deep-dive", 5)
        r.execute("open https://cybershop.training/products?id=42")
        status = r.web_lab_status()
        assert status["last_request"]["path"] == "/products"
        assert status["last_response"]["status_code"] == 200
        assert status["history"][0]["method"] == "GET"

    def test_save_restore_preserves_progress_and_hints(self):
        r = MissionRunner("http-deep-dive", 6)
        r.execute("open https://cybershop.training/products")
        r.use_hint("hd-2")
        r.use_hint("hd-2")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.progress.completed_ids == r.progress.completed_ids
        assert r2.progress.hint_index == {"hd-2": 2}
        assert r2.shell.web_lab.investigation_log == r.shell.web_lab.investigation_log

    def test_save_restore_preserves_bearer_auth_flow(self):
        r = MissionRunner("http-deep-dive", 7)
        r.execute('open -H "Authorization: Bearer training-token-001" '
                 'https://cybershop.training/api/me')
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        out = r2.shell.execute('open -H "Authorization: Bearer training-token-001" '
                               'https://cybershop.training/api/me')
        assert '"username": "student"' in out

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("http-deep-dive", 8)
        r1.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/auth/login')
        r2 = MissionRunner("http-deep-dive", 9)
        assert r2.web_lab_status()["logged_in_as"] is None


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
        u = User(username="hd_test", email="hddive@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "hd_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


WEB_FUNDAMENTALS_SOLVE: list[str] = [
    "open https://cybershop.training/products?id=42",
    "request GET /products",
    "open https://cybershop.training/search?q=linux",
    "open https://cybershop.training/",
    "open https://cybershop.training/does-not-exist",
    "headers",
    ('open -X POST -d "username=student&password=training123" '
     'https://cybershop.training/login'),
    "cookies",
    "open https://cybershop.training/profile",
    "open https://cybershop.training/login",
    "evidence", "inspect 1", "inspect 2", "inspect 3",
    ('echo "Conclusion: the user never submitted the login form, so no session '
     'cookie was ever set - no session cookie" > web/investigation.txt'),
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

            assert mission_status(uid, "http-deep-dive") == "locked"

            start_mission(uid, "web-fundamentals")
            for c in WEB_FUNDAMENTALS_SOLVE:
                execute_command(uid, "web-fundamentals", c)

            assert mission_status(uid, "http-deep-dive") == "available"

            start_mission(uid, "http-deep-dive")
            for c in SOLVE:
                execute_command(uid, "http-deep-dive", c)

            assert mission_status(uid, "http-deep-dive") == "completed"

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
            assert "http-deep-dive" in ids

    def test_terminal_page_shows_inspector(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/http-deep-dive")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "data-inspector-toggle" in body
            assert 'data-tab="request"' in body
            assert 'data-tab="response"' in body
            assert 'data-tab="headers"' in body
            assert 'data-tab="body"' in body
            assert 'data-tab="cookies"' in body
            assert 'data-tab="history"' in body
            assert "data-inspector-form" in body
            assert 'id="tm-web-lab-initial"' in body
            assert "data-web-status" in body  # existing status panel still present

    def test_terminal_page_shows_tls_visual(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/http-deep-dive")
            assert b"tm-tls" in r.data

    def test_execute_returns_full_web_lab_status_for_inspector(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/http-deep-dive")
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "http-deep-dive",
                "command": "open https://cybershop.training/products?id=42",
            })
            assert r.status_code == 200
            d = r.get_json()
            assert d["web_lab_status"]["last_request"] is not None
            assert d["web_lab_status"]["last_response"]["headers"]["ETag"] == '"product-42-v1"'
            assert isinstance(d["web_lab_status"]["history"], list)
