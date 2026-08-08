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
from app.core.terminal.proxy import ProxyLab, build_proxy_lab
from app.core.terminal.shell import Shell
from app.core.terminal.web import HOST, build_request, parse_url

SOLVE: list[str] = [
    "proxy",
    "intercept on",
    "browse https://cybershop.training/products",
    "forward",
    "browse https://cybershop.training/login",
    "drop",
    "browse https://cybershop.training/products?id=42",
    'modify -Q "id=43"',
    "forward",
    "browse https://cybershop.training/products",
    'modify -H "User-Agent: CyberBrowser/2.0"',
    "forward",
    ('browse -X POST -H "Content-Type: application/json" -d \'{"display_name": "Student"}\' '
     "https://cybershop.training/api/profile"),
    "modify -d '{\"display_name\": \"CyberStudent\"}'",
    "forward",
    "proxy-history",
    "send-to-repeater 1",
    'repeater-edit -Q "id=43"',
    "repeater-send",
    'repeater-edit -Q "id=44"',
    "repeater-send",
    "compare 1 2",
    "browse https://google.com/",
    ('echo "Conclusion: modifying the display_name parameter changes the profile response" '
     "> web/proxy-investigation.txt"),
]


# ═══════════════════════════════════════════
# ProxyLab — state machine
# ═══════════════════════════════════════════
class TestProxyLabState:
    def _lab(self) -> ProxyLab:
        return build_proxy_lab()

    def _req(self, method="GET", path="/products", query=None, body="", headers=None):
        url = parse_url(f"https://{HOST}{path}" + (f"?{'&'.join(f'{k}={v}' for k, v in (query or {}).items())}" if query else ""))
        return build_request(method, url, body=body, extra_headers=headers)

    def test_scope_check(self):
        lab = self._lab()
        assert lab.in_scope(HOST)
        assert not lab.in_scope("google.com")
        assert not lab.in_scope("127.0.0.1")
        assert not lab.in_scope("localhost")

    def test_intercept_sets_pending_and_last_intercepted(self):
        lab = self._lab()
        req = self._req()
        lab.intercept(req)
        assert lab.pending_request is req
        assert lab.last_intercepted is req

    def test_dispatch_records_history_immediately(self):
        lab = self._lab()
        req = self._req()
        resp = lab.dispatch(req)
        assert resp.status_code == 200
        assert len(lab.history) == 1
        assert lab.last_request is req

    def test_forward_pending_moves_to_history(self):
        lab = self._lab()
        lab.intercept(self._req())
        resp = lab.forward_pending()
        assert resp is not None
        assert lab.pending_request is None
        assert len(lab.history) == 1

    def test_forward_pending_without_intercept_returns_none(self):
        lab = self._lab()
        assert lab.forward_pending() is None
        assert lab.history == []

    def test_drop_pending_clears_and_counts(self):
        lab = self._lab()
        lab.intercept(self._req())
        assert lab.drop_pending()
        assert lab.pending_request is None
        assert lab.dropped_count == 1
        assert lab.history == []

    def test_drop_without_pending_returns_false(self):
        lab = self._lab()
        assert not lab.drop_pending()
        assert lab.dropped_count == 0

    def test_edit_pending_query_and_forward(self):
        lab = self._lab()
        lab.intercept(self._req(query={"id": "42"}))
        assert lab.edit_pending(query={"id": "43"})
        resp = lab.forward_pending()
        assert lab.last_request.query["id"] == "43"
        assert "Product #43" in resp.body

    def test_edit_pending_header(self):
        lab = self._lab()
        lab.intercept(self._req())
        lab.edit_pending(headers={"User-Agent": "CyberBrowser/2.0"})
        assert lab.pending_request.headers["User-Agent"] == "CyberBrowser/2.0"

    def test_edit_pending_body_updates_content_length(self):
        lab = self._lab()
        lab.intercept(self._req(method="POST", path="/api/profile",
                                headers={"Content-Type": "application/json"},
                                body='{"display_name": "Student"}'))
        lab.edit_pending(body='{"display_name": "CyberStudent"}')
        assert lab.pending_request.body == '{"display_name": "CyberStudent"}'
        assert lab.pending_request.headers["Content-Length"] == str(len('{"display_name": "CyberStudent"}'))

    def test_edit_pending_without_pending_returns_false(self):
        lab = self._lab()
        assert not lab.edit_pending(method="POST")

    def test_history_contains(self):
        lab = self._lab()
        lab.dispatch(self._req(path="/products"))
        assert lab.history_contains("GET", "/products")
        assert not lab.history_contains("GET", "/profile")

    def test_send_to_repeater_copies_request(self):
        lab = self._lab()
        lab.dispatch(self._req(query={"id": "1"}))
        assert lab.send_to_repeater(1)
        assert lab.repeater_request is not None
        assert lab.repeater_request is not lab.history[0][0]
        assert lab.repeater_request.query == {"id": "1"}

    def test_send_to_repeater_out_of_range(self):
        lab = self._lab()
        assert not lab.send_to_repeater(1)
        assert lab.repeater_request is None

    def test_editing_repeater_draft_never_mutates_history(self):
        lab = self._lab()
        lab.dispatch(self._req(query={"id": "1"}))
        lab.send_to_repeater(1)
        lab.edit_repeater(query={"id": "999"})
        assert lab.history[0][0].query == {"id": "1"}
        assert lab.repeater_request.query["id"] == "999"

    def test_send_repeater_logs_and_resets_draft(self):
        lab = self._lab()
        lab.dispatch(self._req(query={"id": "1"}))
        lab.send_to_repeater(1)
        lab.edit_repeater(query={"id": "42"})
        resp = lab.send_repeater()
        assert resp is not None
        assert len(lab.repeater_log) == 1
        # Further edits must not retroactively change the logged entry.
        lab.edit_repeater(query={"id": "43"})
        assert lab.repeater_log[0][0].query["id"] == "42"

    def test_send_repeater_without_draft_returns_none(self):
        lab = self._lab()
        assert lab.send_repeater() is None

    def test_compare_detects_differing_line(self):
        lab = self._lab()
        lab.dispatch(self._req(query={"id": "1"}))
        lab.send_to_repeater(1)
        lab.edit_repeater(query={"id": "42"})
        lab.send_repeater()
        lab.edit_repeater(query={"id": "43"})
        lab.send_repeater()
        result = lab.compare(1, 2)
        assert result is not None
        assert lab.compared is True
        assert "differs" in result

    def test_compare_out_of_range_returns_none(self):
        lab = self._lab()
        assert lab.compare(1, 2) is None
        assert lab.compared is False

    def test_to_dict_from_dict_round_trip(self):
        lab = self._lab()
        lab.intercept_enabled = True
        lab.dispatch(self._req())
        lab.send_to_repeater(1)
        lab.send_repeater()
        lab.blocked_hosts.append("evil.example.com")
        restored = ProxyLab.from_dict(lab.to_dict())
        assert restored.intercept_enabled is True
        assert len(restored.history) == 1
        assert restored.repeater_request is not None
        assert len(restored.repeater_log) == 1
        assert restored.blocked_hosts == ["evil.example.com"]


# ═══════════════════════════════════════════
# Terminal commands
# ═══════════════════════════════════════════
class TestProxyCommands:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.proxy_lab = build_proxy_lab()
        return sh

    def test_commands_fail_gracefully_without_proxy_lab(self):
        sh = Shell()
        assert "no simulated proxy" in sh.execute("proxy")
        assert "no simulated proxy" in sh.execute("intercept on")
        assert "no simulated proxy" in sh.execute("browse https://cybershop.training/")
        assert "no simulated proxy" in sh.execute("forward")
        assert "no simulated proxy" in sh.execute("drop")

    def test_intercept_toggle(self):
        sh = self._shell()
        assert "ON" in sh.execute("intercept on")
        assert sh.proxy_lab.intercept_enabled
        assert "OFF" in sh.execute("intercept off")
        assert not sh.proxy_lab.intercept_enabled

    def test_intercept_requires_valid_arg(self):
        sh = self._shell()
        assert "Usage" in sh.execute("intercept")
        assert "Usage" in sh.execute("intercept sideways")

    def test_browse_with_intercept_off_dispatches_immediately(self):
        sh = self._shell()
        out = sh.execute("browse https://cybershop.training/products")
        assert "REQUEST" in out and "RESPONSE" in out
        assert len(sh.proxy_lab.history) == 1
        assert sh.proxy_lab.pending_request is None

    def test_browse_with_intercept_on_pauses(self):
        sh = self._shell()
        sh.execute("intercept on")
        out = sh.execute("browse https://cybershop.training/products")
        assert "intercepted" in out.lower()
        assert sh.proxy_lab.pending_request is not None
        assert sh.proxy_lab.history == []

    def test_browse_rejects_out_of_scope_host(self):
        sh = self._shell()
        out = sh.execute("browse https://google.com/")
        assert "Outside training scope" in out
        assert "google.com" in sh.proxy_lab.blocked_hosts
        assert sh.proxy_lab.history == []
        assert sh.proxy_lab.pending_request is None

    def test_browse_rejects_out_of_scope_even_with_intercept_on(self):
        sh = self._shell()
        sh.execute("intercept on")
        out = sh.execute("browse https://127.0.0.1/")
        assert "Outside training scope" in out
        assert sh.proxy_lab.pending_request is None

    def test_forward_without_pending(self):
        sh = self._shell()
        assert "Nothing to forward" in sh.execute("forward")

    def test_drop_without_pending(self):
        sh = self._shell()
        assert "Nothing to drop" in sh.execute("drop")

    def test_modify_query_and_forward(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("browse https://cybershop.training/products?id=42")
        sh.execute('modify -Q "id=43"')
        out = sh.execute("forward")
        assert "Product #43" in out
        assert sh.proxy_lab.last_request.query["id"] == "43"

    def test_modify_without_pending(self):
        sh = self._shell()
        assert "No intercepted request" in sh.execute('modify -Q "id=1"')

    def test_proxy_history_lists_forwarded_requests(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products")
        sh.execute("browse https://cybershop.training/")
        out = sh.execute("proxy-history")
        assert "#1  GET /products" in out
        assert "#2  GET /" in out

    def test_proxy_history_empty(self):
        sh = self._shell()
        assert "No requests forwarded yet" in sh.execute("proxy-history")

    def test_send_to_repeater_and_send(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products?id=42")
        sh.execute("send-to-repeater 1")
        assert sh.proxy_lab.repeater_request is not None
        sh.execute('repeater-edit -Q "id=99"')
        out = sh.execute("repeater-send")
        assert "Product #99" in out
        assert len(sh.proxy_lab.repeater_log) == 1

    def test_send_to_repeater_bad_index(self):
        sh = self._shell()
        out = sh.execute("send-to-repeater 5")
        assert "not found" in out

    def test_repeater_send_without_draft(self):
        sh = self._shell()
        assert "Repeater is empty" in sh.execute("repeater-send")

    def test_compare_two_repeater_sends(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products?id=1")
        sh.execute("send-to-repeater 1")
        sh.execute("repeater-send")
        sh.execute('repeater-edit -Q "id=2"')
        sh.execute("repeater-send")
        out = sh.execute("compare 1 2")
        assert "differs" in out
        assert sh.proxy_lab.compared

    def test_compare_bad_usage(self):
        sh = self._shell()
        assert "Usage" in sh.execute("compare")
        assert "Usage" in sh.execute("compare 1 x")

    def test_compare_missing_entries(self):
        sh = self._shell()
        assert "not found" in sh.execute("compare 1 2")


# ═══════════════════════════════════════════
# Validator — proxy_state checks
# ═══════════════════════════════════════════
class TestProxyStateValidator:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.proxy_lab = build_proxy_lab()
        return sh

    def test_no_proxy_lab_fails(self):
        sh = Shell()
        obj = {"id": "x", "xp": 10, "validate": {"type": "proxy_state", "check": "intercept_enabled", "match": "true"}}
        assert not validate(obj, sh).passed

    def test_intercept_enabled(self):
        sh = self._shell()
        sh.execute("intercept on")
        obj = {"id": "x", "xp": 10, "validate": {"type": "proxy_state", "check": "intercept_enabled", "match": "true"}}
        assert validate(obj, sh).passed

    def test_intercepted_check(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("browse https://cybershop.training/products")
        obj = {"id": "x", "xp": 10, "validate": {"type": "proxy_state", "check": "intercepted", "match": "GET /products"}}
        assert validate(obj, sh).passed

    def test_forwarded_check(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products")
        obj = {"id": "x", "xp": 10, "validate": {"type": "proxy_state", "check": "forwarded", "match": "GET /products"}}
        assert validate(obj, sh).passed

    def test_dropped_count(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("browse https://cybershop.training/login")
        sh.execute("drop")
        obj = {"id": "x", "xp": 10, "validate": {"type": "proxy_state", "check": "dropped_count", "match": "1"}}
        assert validate(obj, sh).passed

    def test_query_param_check(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("browse https://cybershop.training/products?id=42")
        sh.execute('modify -Q "id=43"')
        sh.execute("forward")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "query_param", "param": "id", "match": "43"}}
        assert validate(obj, sh).passed

    def test_header_check_request(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("browse https://cybershop.training/products")
        sh.execute('modify -H "User-Agent: CyberBrowser/2.0"')
        sh.execute("forward")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "header", "in": "request",
            "header": "User-Agent", "match": "CyberBrowser/2.0"}}
        assert validate(obj, sh).passed

    def test_body_field_check_request(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute('browse -X POST -H "Content-Type: application/json" '
                  '-d \'{"display_name": "Student"}\' https://cybershop.training/api/profile')
        sh.execute("modify -d '{\"display_name\": \"CyberStudent\"}'")
        sh.execute("forward")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "body_field", "in": "request",
            "field": "display_name", "match": "CyberStudent"}}
        assert validate(obj, sh).passed

    def test_history_contains_check(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "history_contains", "match": "GET /products"}}
        assert validate(obj, sh).passed

    def test_repeater_loaded_check(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products")
        sh.execute("send-to-repeater 1")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "repeater_loaded", "match": "true"}}
        assert validate(obj, sh).passed

    def test_repeater_query_param_check(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products")
        sh.execute("send-to-repeater 1")
        sh.execute('repeater-edit -Q "id=43"')
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "repeater_query_param", "param": "id", "match": "43"}}
        assert validate(obj, sh).passed

    def test_repeater_used_check(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products")
        sh.execute("send-to-repeater 1")
        sh.execute("repeater-send")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "repeater_used", "match": "1"}}
        assert validate(obj, sh).passed

    def test_response_compared_check(self):
        sh = self._shell()
        sh.execute("browse https://cybershop.training/products?id=1")
        sh.execute("send-to-repeater 1")
        sh.execute("repeater-send")
        sh.execute('repeater-edit -Q "id=2"')
        sh.execute("repeater-send")
        sh.execute("compare 1 2")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "response_compared", "match": "true"}}
        assert validate(obj, sh).passed

    def test_scope_blocked_check(self):
        sh = self._shell()
        sh.execute("browse https://google.com/")
        obj = {"id": "x", "xp": 10, "validate": {
            "type": "proxy_state", "check": "scope_blocked", "match": "1"}}
        assert validate(obj, sh).passed

    def test_unknown_check_fails(self):
        sh = self._shell()
        obj = {"id": "x", "xp": 10, "validate": {"type": "proxy_state", "check": "not_a_real_check", "match": "x"}}
        assert not validate(obj, sh).passed


# ═══════════════════════════════════════════
# Security isolation
# ═══════════════════════════════════════════
class TestSecurityIsolation:
    def test_proxy_module_has_no_network_capable_imports(self):
        import ast

        import app.core.terminal.proxy as proxymod
        with open(proxymod.__file__, encoding="utf-8") as f:
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

    def test_external_host_blocked(self):
        sh = Shell()
        sh.proxy_lab = build_proxy_lab()
        out = sh.execute("browse https://evil.example.com/")
        assert "Outside training scope" in out
        assert sh.proxy_lab.history == []

    def test_localhost_blocked(self):
        sh = Shell()
        sh.proxy_lab = build_proxy_lab()
        sh.execute("browse http://localhost/")
        assert "localhost" in sh.proxy_lab.blocked_hosts

    def test_private_ip_blocked(self):
        sh = Shell()
        sh.proxy_lab = build_proxy_lab()
        sh.execute("browse http://192.168.1.1/")
        assert "192.168.1.1" in sh.proxy_lab.blocked_hosts

    def test_127_0_0_1_blocked(self):
        sh = Shell()
        sh.proxy_lab = build_proxy_lab()
        sh.execute("browse http://127.0.0.1/")
        assert "127.0.0.1" in sh.proxy_lab.blocked_hosts

    def test_unknown_route_404_not_a_crash(self):
        sh = Shell()
        sh.proxy_lab = build_proxy_lab()
        out = sh.execute("browse https://cybershop.training/does-not-exist")
        assert "404" in out

    def test_repeater_cannot_escape_scope(self):
        """The Repeater always resends through the same in-scope WebApp —
        there is no path that lets a Repeater draft target a different
        host, since HttpRequest.host is only ever set by build_request()
        against an already scope-checked ParsedUrl."""
        sh = Shell()
        sh.proxy_lab = build_proxy_lab()
        sh.execute("browse https://cybershop.training/products")
        sh.execute("send-to-repeater 1")
        assert sh.proxy_lab.repeater_request.host == HOST
        sh.execute("repeater-send")
        assert sh.proxy_lab.repeater_log[0][0].host == HOST

    def test_proxy_is_not_an_open_proxy(self):
        """Every request the proxy ever dispatches goes through the same
        in-process WebApp.handle(); there is no code path anywhere in
        proxy.py that opens a socket or accepts an arbitrary target host."""
        import app.core.terminal.proxy as proxymod
        with open(proxymod.__file__, encoding="utf-8") as f:
            src = f.read()
        assert "socket." not in src
        assert "requests." not in src


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

    def test_terminal_mission(self):
        m = get_mission("burp-fundamentals")
        assert m["next_mission"] is None

    def test_proxy_lab_flag_set(self):
        m = get_mission("burp-fundamentals")
        assert m["proxy_lab"] is True

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
        r.execute("intercept on")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) < len(r.mission["objectives"])

    def test_partial_progress_persists(self):
        r = MissionRunner("burp-fundamentals", 3)
        r.execute("proxy")
        assert len(r.progress.completed_ids) >= 1

    def test_ai_context_includes_proxy_status(self):
        r = MissionRunner("burp-fundamentals", 4)
        r.execute("intercept on")
        r.execute("browse https://cybershop.training/products")
        ctx = r.ai_context()
        assert ctx["proxy"]["intercept_enabled"] is True
        assert ctx["proxy"]["pending_request"] == "GET /products"

    def test_ai_context_reflects_forwarded_and_dropped(self):
        r = MissionRunner("burp-fundamentals", 5)
        r.execute("browse https://cybershop.training/products")
        r.execute("intercept on")
        r.execute("browse https://cybershop.training/login")
        r.execute("drop")
        ctx = r.ai_context()
        assert ctx["proxy"]["last_forwarded"] == "GET /products"
        assert ctx["proxy"]["dropped_count"] == 1

    def test_proxy_lab_status_carries_full_request_response(self):
        r = MissionRunner("burp-fundamentals", 6)
        r.execute("browse https://cybershop.training/products?id=42")
        status = r.proxy_lab_status()
        assert status["last_request"]["path"] == "/products"
        assert status["last_response"]["status_code"] == 200
        assert status["history"][0]["method"] == "GET"

    def test_save_restore_preserves_progress_and_intercept_state(self):
        r = MissionRunner("burp-fundamentals", 7)
        r.execute("intercept on")
        r.execute("browse https://cybershop.training/products")
        r.use_hint("bf-3")
        r.use_hint("bf-3")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.progress.completed_ids == r.progress.completed_ids
        assert r2.progress.hint_index == {"bf-3": 2}
        assert r2.shell.proxy_lab.intercept_enabled is True
        assert r2.shell.proxy_lab.pending_request is not None

    def test_save_restore_preserves_repeater_and_history(self):
        r = MissionRunner("burp-fundamentals", 8)
        r.execute("browse https://cybershop.training/products?id=42")
        r.execute("send-to-repeater 1")
        r.execute("repeater-send")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert len(r2.shell.proxy_lab.history) == 1
        assert len(r2.shell.proxy_lab.repeater_log) == 1

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("burp-fundamentals", 9)
        r1.execute("intercept on")
        r1.execute("browse https://cybershop.training/login")
        r2 = MissionRunner("burp-fundamentals", 10)
        assert r2.proxy_lab_status()["intercept_enabled"] is False
        assert r2.proxy_lab_status()["pending_request"] is None


# ═══════════════════════════════════════════
# Progressive hints
# ═══════════════════════════════════════════
class TestProgressiveHints:
    def test_first_hint_is_conceptual_not_the_answer(self):
        r = MissionRunner("burp-fundamentals", 11)
        hint = r.use_hint("bf-2")
        assert "intercept on" not in hint.lower()

    def test_hints_escalate(self):
        r = MissionRunner("burp-fundamentals", 12)
        h1 = r.use_hint("bf-2")
        h2 = r.use_hint("bf-2")
        h3 = r.use_hint("bf-2")
        assert h1 != h2 != h3
        assert "intercept on" in h3.lower()

    def test_hints_cap_at_last_level(self):
        r = MissionRunner("burp-fundamentals", 13)
        for _ in range(5):
            last = r.use_hint("bf-2")
        assert "intercept on" in last.lower()

    def test_hints_used_counter_increments(self):
        r = MissionRunner("burp-fundamentals", 14)
        r.use_hint("bf-1")
        r.use_hint("bf-2")
        assert r.progress.hints_used == 2


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
        u = User(username="bf_test", email="bftest@t.io")
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

    def test_terminal_page_shows_proxy_dashboard(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/burp-fundamentals")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "Proxy Dashboard" in body
            assert "data-proxy-intercept-toggle" in body
            assert "data-proxy-forward" in body
            assert "data-proxy-drop" in body
            assert "data-proxy-edit-form" in body
            assert "data-proxy-history" in body
            assert "data-repeater-request" in body
            assert "data-repeater-send" in body
            assert "data-compare-btn" in body
            assert 'id="tm-proxy-lab-initial"' in body

    def test_execute_returns_full_proxy_lab_status(self, app, student):
        # NOTE: this user already fully solved burp-fundamentals in
        # TestServices above (module-scoped fixtures, same in-memory
        # runner) with Intercept left ON — so 'intercept off' is issued
        # first, otherwise this 'browse' would just pause instead of
        # dispatching immediately.
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/burp-fundamentals")
            c.post("/api/terminal/mission/execute", json={
                "slug": "burp-fundamentals", "command": "intercept off"})
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "burp-fundamentals",
                "command": "browse https://cybershop.training/products?id=42",
            })
            assert r.status_code == 200
            d = r.get_json()
            assert d["proxy_lab_status"]["last_request"]["path"] == "/products"
            assert d["proxy_lab_status"]["last_response"]["headers"]["ETag"] == '"product-42-v1"'
            assert isinstance(d["proxy_lab_status"]["history"], list)

    def test_execute_blocks_external_host_over_http(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/burp-fundamentals")
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "burp-fundamentals",
                "command": "browse https://google.com/",
            })
            assert r.status_code == 200
            d = r.get_json()
            assert "Outside training scope" in d["output"]
            # This user's history may already carry an earlier scope
            # violation from TestServices' full solve above — only the
            # membership, not the exact list, is meaningful here.
            assert "google.com" in d["proxy_lab_status"]["blocked_hosts"]
