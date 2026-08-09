"""Tests for YC-035.3 — Authentication & Sessions interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0353-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_as.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell
from app.core.terminal.web import (
    HOST,
    WebApp,
    build_request,
    build_web_lab,
    parse_url,
)

SOLVE: list[str] = [
    "web",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/login',
    "cookies",
    "open https://cybershop.training/profile",
    ('open -X POST -d "username=student&password=wrong-password" '
     'https://cybershop.training/login'),
    "open https://cybershop.training/admin",
    "open https://cybershop.training/api/profile",
    "open -X POST https://cybershop.training/logout",
    "open https://cybershop.training/profile",
    "open https://cybershop.training/dashboard",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/login',
    "expire",
    "evidence", "inspect 1", "inspect 2", "inspect 3", "inspect 4",
    ('echo "Conclusion: logout invalidated the session server-side (Set-Cookie deletion), '
     'so the final /profile request was correctly rejected - not a bug" > '
     'web/auth-investigation.txt'),
]


# ═══════════════════════════════════════════
# WebApp routing — new routes
# ═══════════════════════════════════════════
class TestWebAppRouting:
    def _get(self, app, path, cookies=None):
        url = parse_url(f"https://{HOST}{path}")
        req = build_request("GET", url, cookies=cookies)
        return req, app.handle(req)

    def _login(self, app):
        url = parse_url(f"https://{HOST}/login")
        req = build_request("POST", url, body="username=student&password=training123")
        resp = app.handle(req)
        return resp.cookies["session_id"]

    def test_login_failure_is_json(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/login")
        req = build_request("POST", url, body="username=student&password=wrong")
        resp = app.handle(req)
        assert resp.status_code == 401
        assert resp.content_type == "application/json"
        assert "Invalid training credentials" in resp.body

    def test_account_requires_session_redirects(self):
        app = WebApp()
        _, resp = self._get(app, "/account")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login"

    def test_account_with_session(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._get(app, "/account", cookies={"session_id": sid})
        assert resp.status_code == 200
        assert "student" in resp.body

    def test_dashboard_requires_session_redirects(self):
        app = WebApp()
        _, resp = self._get(app, "/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login"

    def test_dashboard_with_session(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._get(app, "/dashboard", cookies={"session_id": sid})
        assert resp.status_code == 200

    def test_admin_unauthenticated_401(self):
        app = WebApp()
        _, resp = self._get(app, "/admin")
        assert resp.status_code == 401

    def test_admin_authenticated_non_admin_403(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._get(app, "/admin", cookies={"session_id": sid})
        assert resp.status_code == 403
        assert resp.content_type == "application/json"

    def test_admin_as_admin_user_200(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/login")
        req = build_request("POST", url, body="username=admin&password=admin123")
        resp = app.handle(req)
        sid = resp.cookies["session_id"]
        _, resp2 = self._get(app, "/admin", cookies={"session_id": sid})
        assert resp2.status_code == 200

    def test_post_logout_redirects_to_login_and_deletes_cookie(self):
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/logout")
        req = build_request("POST", url, cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login"
        assert "session_id" in resp.deleted_cookies
        assert sid not in app.sessions

    def test_get_logout_still_redirects_home(self):
        # Backward compatible with every earlier mission (YC-035.0-.2).
        app = WebApp()
        sid = self._login(app)
        _, resp = self._get(app, "/logout", cookies={"session_id": sid})
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"
        assert "session_id" in resp.deleted_cookies

    def test_expire_session_invalidates_server_side(self):
        app = WebApp()
        sid = self._login(app)
        assert app.expire_session(sid) is True
        assert sid not in app.sessions
        # Requesting a protected route with the (now stale) cookie fails.
        _, resp = self._get(app, "/profile", cookies={"session_id": sid})
        assert resp.status_code == 401

    def test_expire_unknown_session_returns_false(self):
        app = WebApp()
        assert app.expire_session("not-a-real-session") is False

    def test_render_response_shows_cookie_deletion(self):
        from app.core.terminal.web import render_response
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/logout")
        req = build_request("POST", url, cookies={"session_id": sid})
        resp = app.handle(req)
        text = render_response(resp)
        assert "Set-Cookie: session_id=; Max-Age=0" in text

    def test_existing_profile_401_behavior_unchanged(self):
        # Locked contract from YC-035.0 — must not regress.
        app = WebApp()
        _, resp = self._get(app, "/profile")
        assert resp.status_code == 401

    def test_existing_api_me_still_bearer_only(self):
        # Locked contract from YC-035.1 — /api/me deliberately does not
        # accept a session cookie; this mission uses /api/profile instead
        # for cookie-based API auth (see docs/AUTHENTICATION_AND_SESSIONS.md).
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/api/me")
        req = build_request("GET", url, cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 401


# ═══════════════════════════════════════════
# WebSession — cookie deletion handling
# ═══════════════════════════════════════════
class TestWebSessionCookieDeletion:
    def test_record_clears_deleted_cookie_from_jar(self):
        sh = Shell()
        sh.web_lab = build_web_lab("auth-lifecycle")
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        assert "session_id" in sh.web_lab.session.cookies
        sh.execute("open -X POST https://cybershop.training/logout")
        assert "session_id" not in sh.web_lab.session.cookies


# ═══════════════════════════════════════════
# Terminal commands — 'expire'
# ═══════════════════════════════════════════
class TestExpireCommand:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.web_lab = build_web_lab("auth-lifecycle")
        return sh

    def test_no_lab_configured(self):
        sh = Shell()
        assert "no simulated web environment" in sh.execute("expire")

    def test_expire_without_login(self):
        sh = self._shell()
        assert "No active session" in sh.execute("expire")

    def test_expire_after_login(self):
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        out = sh.execute("expire")
        assert "expired" in out.lower()
        assert sh.web_lab.expired_count == 1
        # Cookie is still in the jar — expiration doesn't clear it.
        assert "session_id" in sh.web_lab.session.cookies
        # But the server no longer honors it.
        out2 = sh.execute("open https://cybershop.training/profile")
        assert "401" in out2


# ═══════════════════════════════════════════
# Validator — new checks
# ═══════════════════════════════════════════
class TestAuthValidatorChecks:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab("auth-lifecycle")
        return sh

    def _obj(self, check, match="1", **extra):
        v = {"type": "web_state", "check": check, "match": match}
        v.update(extra)
        return {"id": "x", "xp": 10, "validate": v}

    def test_cookie_sent(self):
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        obj = self._obj("cookie_sent", "student-session", cookie_name="session_id")
        assert not validate(obj, sh).passed  # cookie received, not yet sent
        sh.execute("open https://cybershop.training/profile")
        assert validate(obj, sh).passed

    def test_logout_completed(self):
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        obj = self._obj("logout_completed")
        assert not validate(obj, sh).passed
        sh.execute("open -X POST https://cybershop.training/logout")
        assert validate(obj, sh).passed

    def test_session_expired(self):
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        obj = self._obj("session_expired")
        assert not validate(obj, sh).passed
        sh.execute("expire")
        assert validate(obj, sh).passed

    def test_checks_fail_gracefully_without_web_lab(self):
        sh = Shell()
        assert not validate(self._obj("cookie_sent", "x"), sh).passed
        assert not validate(self._obj("logout_completed"), sh).passed
        assert not validate(self._obj("session_expired"), sh).passed


# ═══════════════════════════════════════════
# Investigation scenario
# ═══════════════════════════════════════════
class TestInvestigationScenario:
    def test_auth_lifecycle_scenario(self):
        lab = build_web_lab("auth-lifecycle")
        assert len(lab.investigation_log) == 4
        logout_req, logout_resp = lab.investigation_log[2]
        assert logout_req.path == "/logout"
        assert "session_id" in logout_resp.deleted_cookies
        last_req, last_resp = lab.investigation_log[-1]
        assert last_req.path == "/profile"
        assert last_resp.status_code == 401

    def test_scenario_is_deterministic(self):
        a = build_web_lab("auth-lifecycle")
        b = build_web_lab("auth-lifecycle")
        assert a.investigation_log == b.investigation_log

    def test_scenario_never_touches_live_session(self):
        lab = build_web_lab("auth-lifecycle")
        assert lab.session.history == []
        assert lab.session.cookies == {}


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "authentication-sessions" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("authentication-sessions")
        assert m is not None
        assert m["title"] == "Authentication & Sessions"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 600

    def test_objective_count(self):
        m = get_mission("authentication-sessions")
        assert len(m["objectives"]) == 15

    def test_xp_sums_to_total(self):
        m = get_mission("authentication-sessions")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_every_objective_has_progressive_hints(self):
        m = get_mission("authentication-sessions")
        for o in m["objectives"]:
            assert "hints" in o
            assert len(o["hints"]) >= 2

    def test_chained_after_burp_fundamentals(self):
        assert MISSIONS["burp-fundamentals"]["next_mission"] == "authentication-sessions"

    def test_terminal_mission(self):
        m = get_mission("authentication-sessions")
        assert m["next_mission"] is None

    def test_web_lab_scenario_set(self):
        m = get_mission("authentication-sessions")
        assert m["web_lab"] == "auth-lifecycle"

    def test_web_workspace_seeded(self):
        m = get_mission("authentication-sessions")
        assert "web" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("authentication-sessions", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 600
        assert sorted(r.progress.completed_ids) == sorted(
            o["id"] for o in r.mission["objectives"])

    def test_no_premature_completion(self):
        r = MissionRunner("authentication-sessions", 2)
        r.execute("web")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) < len(r.mission["objectives"])

    def test_web_lab_status_carries_auth_fields(self):
        r = MissionRunner("authentication-sessions", 3)
        r.execute('open -X POST -d "username=student&password=training123" '
                 'https://cybershop.training/login')
        status = r.web_lab_status()
        assert status["authenticated"] is True
        assert status["session_present"] is True
        assert status["expired_count"] == 0

    def test_web_lab_status_reflects_expiration(self):
        r = MissionRunner("authentication-sessions", 4)
        r.execute('open -X POST -d "username=student&password=training123" '
                 'https://cybershop.training/login')
        r.execute("expire")
        status = r.web_lab_status()
        assert status["authenticated"] is False
        assert status["session_present"] is True  # cookie still in the jar
        assert status["expired_count"] == 1

    def test_ai_context_includes_masked_session_and_auth_state(self):
        r = MissionRunner("authentication-sessions", 5)
        r.execute('open -X POST -d "username=student&password=training123" '
                 'https://cybershop.training/login')
        ctx = r.ai_context()
        assert ctx["web"]["authentication_state"] == "authenticated"
        assert ctx["web"]["session_active"] is True
        assert ctx["web"]["session_id_present"] is True
        sid_masked = ctx["web"]["session_id_masked"]
        assert sid_masked is not None
        assert "student-session" not in sid_masked
        assert sid_masked.endswith("****")

    def test_ai_context_reflects_logout(self):
        r = MissionRunner("authentication-sessions", 6)
        r.execute('open -X POST -d "username=student&password=training123" '
                 'https://cybershop.training/login')
        r.execute("open -X POST https://cybershop.training/logout")
        ctx = r.ai_context()
        assert ctx["web"]["authentication_state"] == "unauthenticated"
        assert ctx["web"]["session_active"] is False

    def test_save_restore_preserves_expired_count(self):
        r = MissionRunner("authentication-sessions", 7)
        r.execute('open -X POST -d "username=student&password=training123" '
                 'https://cybershop.training/login')
        r.execute("expire")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.shell.web_lab.expired_count == 1

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("authentication-sessions", 8)
        r1.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        assert MissionRunner("authentication-sessions", 9).shell.web_lab.expired_count == 0


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

    def test_new_routes_reject_external_host(self):
        sh = Shell()
        sh.web_lab = build_web_lab("auth-lifecycle")
        for path in ("/account", "/dashboard", "/admin", "/logout"):
            out = sh.execute(f"open -X POST https://evil.example.com{path}")
            assert out == "External hosts are not available in the training environment."

    def test_no_real_credentials_anywhere_in_module(self):
        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read().lower()
        # Only the fixed, documented training password may appear.
        assert "training123" in src
        for weak in ("password123", "letmein", "qwerty", "admin@yushacyber.com"):
            assert weak not in src

    def test_expire_only_affects_the_isolated_lab_instance(self):
        sh1 = Shell()
        sh1.web_lab = build_web_lab("auth-lifecycle")
        sh2 = Shell()
        sh2.web_lab = build_web_lab("auth-lifecycle")
        sh1.execute('open -X POST -d "username=student&password=training123" '
                   'https://cybershop.training/login')
        sh1.execute("expire")
        assert sh1.web_lab.expired_count == 1
        assert sh2.web_lab.expired_count == 0


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
        u = User(username="as_test", email="authsess@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "as_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


BURP_SOLVE: list[str] = [
    "proxy",
    "intercept on",
    "open https://cybershop.training/products",
    "forward",
    "open https://cybershop.training/search?q=linux",
    "drop",
    "open https://cybershop.training/products?id=42",
    "edit query id 43",
    "forward",
    "open https://cybershop.training/products",
    "edit header User-Agent CyberBrowser/2.0",
    "forward",
    "intercept off",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login',
    "intercept on",
    ('open -X POST -H "Content-Type: application/json" -d \'{"display_name": "Student"}\' '
     'https://cybershop.training/api/profile'),
    'edit body \'{"display_name": "CyberStudent"}\'',
    "forward",
    "requests",
    "repeater 2",
    "edit query id 77",
    "repeater send",
    "compare 2 6",
    "open https://evil.example.com/",
    ('open -X POST -H "Content-Type: application/json" -d \'{"Display_Name": "Alex Rivera"}\' '
     'https://cybershop.training/api/profile'),
    "forward",
    ('open -X POST -H "Content-Type: application/json" -d \'{"display_name": "Alex Rivera"}\' '
     'https://cybershop.training/api/profile'),
    "forward",
    "repeater 8",
    "repeater send",
    "compare 7 9",
    ('echo "Conclusion: the POST body used the wrong field name Display_Name instead of '
     'display_name, so the update was silently ignored." > web/proxy-investigation.txt'),
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

            assert mission_status(uid, "authentication-sessions") == "locked"

            start_mission(uid, "burp-fundamentals")
            for c in BURP_SOLVE:
                execute_command(uid, "burp-fundamentals", c)

            assert mission_status(uid, "authentication-sessions") == "available"

            start_mission(uid, "authentication-sessions")
            for c in SOLVE:
                execute_command(uid, "authentication-sessions", c)

            assert mission_status(uid, "authentication-sessions") == "completed"

            user = User.query.get(uid)
            assert user.xp > 0
            assert user.level >= 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] >= 1


# ═══════════════════════════════════════════
# HTTP — pages / UI reachability
# ═══════════════════════════════════════════
class TestHTTP:
    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "authentication-sessions" in ids

    def test_terminal_page_shows_session_panel(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/authentication-sessions")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "data-session-badge" in body
            assert "data-session-logout" in body
            assert "data-session-expire" in body
            assert "data-session-user" in body
            assert "data-session-id" in body
            assert "data-session-expires" in body
            # Proxy Control (reused from YC-035.2) also present for this mission.
            assert "data-proxy-badge" in body
            # Inspector (reused from YC-035.1) still present too.
            assert "data-inspector-toggle" in body

    def test_session_panel_not_shown_on_other_missions(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/burp-fundamentals")
            body = r.data.decode("utf-8")
            assert "data-session-badge" not in body

    def test_execute_returns_auth_state(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/authentication-sessions")
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "authentication-sessions",
                "command": ('open -X POST -d "username=student&password=training123" '
                           'https://cybershop.training/login'),
            })
            assert r.status_code == 200
            d = r.get_json()
            assert d["web_lab_status"]["authenticated"] is True
