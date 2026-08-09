"""Tests for YC-035.2 — Burp Suite Fundamentals interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0352-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_bf.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell
from app.core.terminal.web import (
    HOST,
    ProxyState,
    WebApp,
    build_request,
    build_web_lab,
    parse_url,
)

SOLVE: list[str] = [
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


# ═══════════════════════════════════════════
# ProxyState model
# ═══════════════════════════════════════════
class TestProxyStateModel:
    def test_defaults(self):
        p = ProxyState()
        assert p.intercept_enabled is False
        assert p.pending is None
        assert p.repeater_request is None
        assert p.intercepted_count == 0

    def test_round_trip_empty(self):
        p = ProxyState()
        assert ProxyState.from_dict(p.to_dict()).to_dict() == p.to_dict()

    def test_round_trip_with_pending_and_repeater(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        sh.execute("intercept on")
        sh.execute("open https://cybershop.training/products")
        sh.web_lab.proxy.repeater_request = sh.web_lab.proxy.pending
        d = sh.web_lab.proxy.to_dict()
        restored = ProxyState.from_dict(d)
        assert restored.pending.path == "/products"
        assert restored.repeater_request.path == "/products"
        assert restored.intercept_enabled is True


# ═══════════════════════════════════════════
# Simulated profile storage
# ═══════════════════════════════════════════
class TestProfileStorage:
    def _logged_in_app(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/auth/login")
        req = build_request("POST", url, body="username=student&password=training123")
        sid = app.handle(req).cookies["session_id"]
        return app, sid

    def test_get_defaults_to_username(self):
        app, sid = self._logged_in_app()
        url = parse_url(f"https://{HOST}/api/profile")
        req = build_request("GET", url, cookies={"session_id": sid})
        resp = app.handle(req)
        assert '"display_name": "student"' in resp.body

    def test_post_correct_key_updates(self):
        app, sid = self._logged_in_app()
        url = parse_url(f"https://{HOST}/api/profile")
        req = build_request("POST", url, body='{"display_name": "CyberStudent"}',
                            cookies={"session_id": sid},
                            extra_headers={"Content-Type": "application/json"})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert '"display_name": "CyberStudent"' in resp.body

        get_req = build_request("GET", url, cookies={"session_id": sid})
        get_resp = app.handle(get_req)
        assert '"display_name": "CyberStudent"' in get_resp.body

    def test_post_wrong_key_is_silently_ignored(self):
        app, sid = self._logged_in_app()
        url = parse_url(f"https://{HOST}/api/profile")
        req = build_request("POST", url, body='{"Display_Name": "Alex Rivera"}',
                            cookies={"session_id": sid},
                            extra_headers={"Content-Type": "application/json"})
        resp = app.handle(req)
        # Still 200 — the bug is invisible at the status-code level.
        assert resp.status_code == 200
        assert '"display_name": "student"' in resp.body  # unchanged

    def test_profiles_isolated_per_app_instance(self):
        app1, sid1 = self._logged_in_app()
        url = parse_url(f"https://{HOST}/api/profile")
        app1.handle(build_request("POST", url, body='{"display_name": "X"}',
                                  cookies={"session_id": sid1},
                                  extra_headers={"Content-Type": "application/json"}))
        app2, sid2 = self._logged_in_app()
        resp = app2.handle(build_request("GET", url, cookies={"session_id": sid2}))
        assert '"display_name": "student"' in resp.body


# ═══════════════════════════════════════════
# Intercept / forward / drop
# ═══════════════════════════════════════════
class TestInterceptForwardDrop:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        return sh

    def test_intercept_off_by_default(self):
        sh = self._shell()
        assert "OFF" in sh.execute("intercept")

    def test_intercept_on_off_toggle(self):
        sh = self._shell()
        assert "now ON" in sh.execute("intercept on")
        assert sh.web_lab.proxy.intercept_enabled is True
        assert "now OFF" in sh.execute("intercept off")
        assert sh.web_lab.proxy.intercept_enabled is False

    def test_open_passes_through_when_intercept_off(self):
        # Regression guard: YC-035.0/YC-035.1 never turn intercept on, so
        # 'open' must behave exactly as before for them.
        sh = self._shell()
        out = sh.execute("open https://cybershop.training/products")
        assert "intercepted" not in out.lower()
        assert sh.web_lab.session.last_response is not None
        assert sh.web_lab.proxy.pending is None

    def test_open_queues_when_intercept_on(self):
        sh = self._shell()
        sh.execute("intercept on")
        out = sh.execute("open https://cybershop.training/products")
        assert "intercepted" in out.lower()
        assert sh.web_lab.proxy.pending is not None
        assert sh.web_lab.proxy.pending.path == "/products"
        assert sh.web_lab.session.last_response is None  # never reached the server
        assert sh.web_lab.proxy.intercepted_count == 1

    def test_forward_sends_and_records(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("open https://cybershop.training/products")
        out = sh.execute("forward")
        assert "forwarded" in out.lower()
        assert sh.web_lab.proxy.pending is None
        assert sh.web_lab.proxy.forwarded_count == 1
        assert len(sh.web_lab.session.history) == 1
        assert sh.web_lab.session.last_response.status_code == 200

    def test_forward_with_nothing_pending(self):
        sh = self._shell()
        out = sh.execute("forward")
        assert "no intercepted request" in out.lower()

    def test_drop_discards_without_reaching_server(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("open https://cybershop.training/products")
        out = sh.execute("drop")
        assert "dropped" in out.lower()
        assert sh.web_lab.proxy.pending is None
        assert sh.web_lab.proxy.dropped_count == 1
        assert len(sh.web_lab.session.history) == 0  # never reached the server

    def test_drop_with_nothing_pending(self):
        sh = self._shell()
        out = sh.execute("drop")
        assert "no intercepted request" in out.lower()

    def test_scope_block_increments_counter(self):
        sh = self._shell()
        out = sh.execute("open https://evil.example.com/")
        assert out == "External hosts are not available in the training environment."
        assert sh.web_lab.proxy.blocked_count == 1

    def test_scope_block_works_even_with_intercept_on(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("open https://evil.example.com/")
        assert sh.web_lab.proxy.blocked_count == 1
        assert sh.web_lab.proxy.pending is None  # never queued


# ═══════════════════════════════════════════
# Edit
# ═══════════════════════════════════════════
class TestEdit:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        sh.execute("intercept on")
        return sh

    def test_edit_nothing_pending_errors(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        out = sh.execute("edit query id 43")
        assert "nothing to edit" in out.lower()

    def test_edit_method(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products")
        sh.execute("edit method POST")
        assert sh.web_lab.proxy.pending.method == "POST"

    def test_edit_path(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products")
        sh.execute("edit path /search")
        assert sh.web_lab.proxy.pending.path == "/search"

    def test_edit_query(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products?id=42")
        sh.execute("edit query id 99")
        assert sh.web_lab.proxy.pending.query["id"] == "99"

    def test_edit_header(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products")
        sh.execute("edit header User-Agent CyberBrowser/2.0")
        assert sh.web_lab.proxy.pending.headers["User-Agent"] == "CyberBrowser/2.0"

    def test_edit_body(self):
        sh = self._shell()
        sh.execute('open -X POST -H "Content-Type: application/json" -d \'{"a": "b"}\' '
                  'https://cybershop.training/api/profile')
        sh.execute('edit body \'{"display_name": "X"}\'')
        assert sh.web_lab.proxy.pending.body == '{"display_name": "X"}'

    def test_edit_prefers_pending_over_repeater(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products?id=1")
        sh.web_lab.proxy.repeater_request = sh.web_lab.proxy.pending
        sh.execute("open https://cybershop.training/search?q=x")  # new pending
        sh.execute("edit query test yes")
        assert "test" in sh.web_lab.proxy.pending.query
        assert "test" not in sh.web_lab.proxy.repeater_request.query


# ═══════════════════════════════════════════
# Repeater
# ═══════════════════════════════════════════
class TestRepeater:
    def _shell_with_history(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        sh.execute("open https://cybershop.training/products?id=42")
        sh.execute("open https://cybershop.training/products?id=43")
        return sh

    def test_repeater_no_history_error(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        out = sh.execute("repeater")
        assert "no requests in history" in out.lower()

    def test_repeater_defaults_to_most_recent(self):
        sh = self._shell_with_history()
        sh.execute("repeater")
        assert sh.web_lab.proxy.repeater_request.query["id"] == "43"
        assert sh.web_lab.proxy.repeater_loaded_count == 1

    def test_repeater_by_index(self):
        sh = self._shell_with_history()
        sh.execute("repeater 1")
        assert sh.web_lab.proxy.repeater_request.query["id"] == "42"

    def test_repeater_out_of_range(self):
        sh = self._shell_with_history()
        out = sh.execute("repeater 99")
        assert "not found" in out.lower()

    def test_repeater_editing_does_not_mutate_history(self):
        sh = self._shell_with_history()
        sh.execute("repeater 1")
        sh.execute("edit query id 999")
        assert sh.web_lab.proxy.repeater_request.query["id"] == "999"
        assert sh.web_lab.session.history[0][0].query["id"] == "42"  # untouched

    def test_repeater_send_with_nothing_loaded(self):
        sh = self._shell_with_history()
        out = sh.execute("repeater send")
        assert "nothing loaded" in out.lower()

    def test_repeater_send_records_new_history_entry(self):
        sh = self._shell_with_history()
        sh.execute("repeater 1")
        sh.execute("edit query id 777")
        out = sh.execute("repeater send")
        assert "sent" in out.lower()
        assert len(sh.web_lab.session.history) == 3
        assert sh.web_lab.session.last_request.query["id"] == "777"
        assert sh.web_lab.proxy.repeater_sent_count == 1


# ═══════════════════════════════════════════
# Compare
# ═══════════════════════════════════════════
class TestCompare:
    def _shell_with_history(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        sh.execute("open https://cybershop.training/products?id=42")
        sh.execute("open https://cybershop.training/products?id=43")
        return sh

    def test_compare_bad_args(self):
        sh = self._shell_with_history()
        assert "usage" in sh.execute("compare").lower()
        assert "usage" in sh.execute("compare 1").lower()

    def test_compare_out_of_range(self):
        sh = self._shell_with_history()
        assert "not found" in sh.execute("compare 1 99").lower()

    def test_compare_finds_difference(self):
        sh = self._shell_with_history()
        out = sh.execute("compare 1 2")
        assert "Product #42" in out
        assert "Product #43" in out
        assert sh.web_lab.proxy.compared_count == 1

    def test_compare_identical_entries_reports_no_differences(self):
        sh = self._shell_with_history()
        out = sh.execute("compare 1 1")
        assert "no differences" in out.lower()


# ═══════════════════════════════════════════
# Investigation scenario
# ═══════════════════════════════════════════
class TestInvestigationScenario:
    def test_profile_mismatch_scenario(self):
        lab = build_web_lab("profile-mismatch")
        assert len(lab.investigation_log) == 4
        last_req, last_resp = lab.investigation_log[-1]
        assert last_req.path == "/api/profile"
        assert '"display_name": "student"' in last_resp.body  # still the old name

    def test_profile_mismatch_scenario_is_deterministic(self):
        a = build_web_lab("profile-mismatch")
        b = build_web_lab("profile-mismatch")
        assert a.investigation_log == b.investigation_log

    def test_scenario_never_touches_live_session(self):
        lab = build_web_lab("profile-mismatch")
        assert lab.session.history == []
        assert lab.session.cookies == {}


# ═══════════════════════════════════════════
# Validator — new proxy checks
# ═══════════════════════════════════════════
class TestProxyValidatorChecks:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        return sh

    def _obj(self, check, match="1", **extra):
        v = {"type": "web_state", "check": check, "match": match}
        v.update(extra)
        return {"id": "x", "xp": 10, "validate": v}

    def test_proxy_enabled(self):
        sh = self._shell()
        assert not validate(self._obj("proxy_enabled", "true"), sh).passed
        sh.execute("intercept on")
        assert validate(self._obj("proxy_enabled", "true"), sh).passed

    def test_request_intercepted(self):
        sh = self._shell()
        assert not validate(self._obj("request_intercepted"), sh).passed
        sh.execute("intercept on")
        sh.execute("open https://cybershop.training/products")
        assert validate(self._obj("request_intercepted"), sh).passed

    def test_request_forwarded(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("open https://cybershop.training/products")
        assert not validate(self._obj("request_forwarded"), sh).passed
        sh.execute("forward")
        assert validate(self._obj("request_forwarded"), sh).passed

    def test_request_dropped(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("open https://cybershop.training/products")
        sh.execute("drop")
        assert validate(self._obj("request_dropped"), sh).passed

    def test_repeater_used(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products")
        assert not validate(self._obj("repeater_used"), sh).passed
        sh.execute("repeater")
        assert validate(self._obj("repeater_used"), sh).passed

    def test_repeater_sent(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products")
        sh.execute("repeater")
        assert not validate(self._obj("repeater_sent"), sh).passed
        sh.execute("repeater send")
        assert validate(self._obj("repeater_sent"), sh).passed

    def test_response_compared(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products?id=1")
        sh.execute("open https://cybershop.training/products?id=2")
        assert not validate(self._obj("response_compared"), sh).passed
        sh.execute("compare 1 2")
        assert validate(self._obj("response_compared"), sh).passed

    def test_scope_blocked(self):
        sh = self._shell()
        assert not validate(self._obj("scope_blocked"), sh).passed
        sh.execute("open https://evil.example.com/")
        assert validate(self._obj("scope_blocked"), sh).passed

    def test_checks_fail_gracefully_without_web_lab(self):
        sh = Shell()
        assert not validate(self._obj("proxy_enabled", "true"), sh).passed


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "burp-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("burp-fundamentals")
        assert m is not None
        assert m["title"] == "Burp Suite Fundamentals"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 550

    def test_objective_count(self):
        m = get_mission("burp-fundamentals")
        assert len(m["objectives"]) == 14

    def test_xp_sums_to_total(self):
        m = get_mission("burp-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_every_objective_has_progressive_hints(self):
        m = get_mission("burp-fundamentals")
        for o in m["objectives"]:
            assert "hints" in o
            assert len(o["hints"]) >= 2

    def test_chained_after_http_deep_dive(self):
        assert MISSIONS["http-deep-dive"]["next_mission"] == "burp-fundamentals"

    def test_chains_into_authentication_sessions(self):
        m = get_mission("burp-fundamentals")
        assert m["next_mission"] == "authentication-sessions"

    def test_web_lab_scenario_set(self):
        m = get_mission("burp-fundamentals")
        assert m["web_lab"] == "profile-mismatch"

    def test_web_workspace_seeded(self):
        m = get_mission("burp-fundamentals")
        assert "web" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("burp-fundamentals", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 550
        assert sorted(r.progress.completed_ids) == sorted(
            o["id"] for o in r.mission["objectives"])

    def test_no_premature_completion(self):
        r = MissionRunner("burp-fundamentals", 2)
        r.execute("proxy")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) < len(r.mission["objectives"])

    def test_ai_context_includes_proxy_summary(self):
        r = MissionRunner("burp-fundamentals", 3)
        r.execute("intercept on")
        r.execute("open https://cybershop.training/products")
        ctx = r.ai_context()
        assert ctx["web"]["proxy"]["intercept_enabled"] is True
        assert ctx["web"]["proxy"]["pending_request"] == "GET /products"
        assert ctx["web"]["proxy"]["intercepted_count"] == 1

    def test_web_lab_status_carries_proxy_state(self):
        r = MissionRunner("burp-fundamentals", 4)
        r.execute("intercept on")
        r.execute("open https://cybershop.training/products")
        status = r.web_lab_status()
        assert status["proxy"]["intercept_enabled"] is True
        assert status["proxy"]["pending"]["path"] == "/products"

    def test_save_restore_preserves_proxy_state(self):
        r = MissionRunner("burp-fundamentals", 5)
        r.execute("intercept on")
        r.execute("open https://cybershop.training/products")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.shell.web_lab.proxy.intercept_enabled is True
        assert r2.shell.web_lab.proxy.pending.path == "/products"
        assert r2.shell.web_lab.proxy.intercepted_count == 1

    def test_save_restore_preserves_repeater_after_forward(self):
        r = MissionRunner("burp-fundamentals", 6)
        r.execute("open https://cybershop.training/products?id=5")
        r.execute("repeater")
        r.execute("edit query id 9")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.shell.web_lab.proxy.repeater_request.query["id"] == "9"

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("burp-fundamentals", 7)
        r1.execute("intercept on")
        assert MissionRunner("burp-fundamentals", 8).shell.web_lab.proxy.intercept_enabled is False


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

    def test_commands_module_has_no_network_capable_imports(self):
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
                    "urllib.request", "shutil", "ftplib", "smtplib"}
        assert not (imported_modules & forbidden)

    def test_external_host_still_rejected_with_intercept_on(self):
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        sh.execute("intercept on")
        out = sh.execute("open https://evil.example.com/")
        assert out == "External hosts are not available in the training environment."
        assert sh.web_lab.session.last_request is None
        assert sh.web_lab.proxy.pending is None

    def test_repeater_cannot_escape_scope(self):
        # Repeater only ever replays a request already built against the
        # simulated host (via 'open'/'request', which reject anything
        # else before a request object exists) — there's no way to load a
        # fabricated out-of-scope request into it.
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        sh.execute("open https://cybershop.training/products")
        sh.execute("repeater")
        assert sh.web_lab.proxy.repeater_request.host == HOST

    def test_proxy_is_not_an_open_proxy(self):
        # 'edit path'/'edit query' can only change the path/query of an
        # already-scoped request — they never touch .host, so there's no
        # way to redirect the simulated request elsewhere.
        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        sh.execute("intercept on")
        sh.execute("open https://cybershop.training/products")
        sh.execute("edit path /../../evil.example.com")
        assert sh.web_lab.proxy.pending.host == HOST


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
        u = User(username="bf_test", email="burpfund@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "bf_test", uid


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

HTTP_DEEP_DIVE_SOLVE: list[str] = [
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

            assert mission_status(uid, "burp-fundamentals") == "locked"

            start_mission(uid, "web-fundamentals")
            for c in WEB_FUNDAMENTALS_SOLVE:
                execute_command(uid, "web-fundamentals", c)

            start_mission(uid, "http-deep-dive")
            for c in HTTP_DEEP_DIVE_SOLVE:
                execute_command(uid, "http-deep-dive", c)

            assert mission_status(uid, "burp-fundamentals") == "available"

            start_mission(uid, "burp-fundamentals")
            for c in SOLVE:
                execute_command(uid, "burp-fundamentals", c)

            assert mission_status(uid, "burp-fundamentals") == "completed"

            user = User.query.get(uid)
            assert user.xp > 0
            assert user.level >= 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] >= 3


# ═══════════════════════════════════════════
# HTTP — pages / UI reachability
# ═══════════════════════════════════════════
class TestHTTP:
    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "burp-fundamentals" in ids

    def test_terminal_page_shows_proxy_control(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/burp-fundamentals")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "data-proxy-badge" in body
            assert "data-proxy-toggle" in body
            assert "data-proxy-pending-box" in body
            assert "data-proxy-forward" in body
            assert "data-proxy-drop" in body
            assert "data-proxy-repeater-send" in body
            assert "data-proxy-compare" in body
            # Inspector (reused from YC-035.1) still present too.
            assert "data-inspector-toggle" in body

    def test_proxy_panel_not_shown_on_other_missions(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/http-deep-dive")
            body = r.data.decode("utf-8")
            assert "data-proxy-badge" not in body

    def test_execute_returns_proxy_state(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/burp-fundamentals")
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "burp-fundamentals",
                "command": "intercept on",
            })
            assert r.status_code == 200
            d = r.get_json()
            assert d["web_lab_status"]["proxy"]["intercept_enabled"] is True
