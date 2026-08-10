"""Tests for YC-035.5 — Cross-Site Scripting (XSS) Fundamentals mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0355-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_xss.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell
from app.core.terminal.web import (
    CSP_POLICY,
    HOST,
    TRAINING_XSS_MARKERS,
    WebApp,
    build_request,
    build_web_lab,
    has_xss_marker,
    parse_url,
)

MARKER = TRAINING_XSS_MARKERS[0]

SOLVE: list[str] = [
    "web",
    "open https://cybershop.training/search?q=laptop",
    f'open "https://cybershop.training/search?q={MARKER}"',
    "intercept on",
    "open https://cybershop.training/search?q=keyboard",
    "forward",
    "intercept off",
    f'open -X POST -d "name=student&comment={MARKER}" https://cybershop.training/feedback',
    "open https://cybershop.training/comments",
    "open https://cybershop.training/dom-demo",
    f'open "https://cybershop.training/dom-demo?input={MARKER}"',
    f'open "https://cybershop.training/secure-search?q={MARKER}"',
    "evidence",
    "inspect 1", "inspect 2", "inspect 3", "inspect 4", "inspect 5",
    ('echo "Conclusion: the search and comments endpoints reflect and store the '
     "training marker unsafely as HTML - reflected and stored XSS. The secure "
     "endpoint shows the same marker safely HTML-escaped, proving output encoding "
     'is the correct defensive control." > web/xss-investigation.txt'),
]


# ═══════════════════════════════════════════
# WebApp routing — new/extended routes
# ═══════════════════════════════════════════
class TestWebAppRouting:
    def _get(self, app, path, query=None):
        url = parse_url(f"https://{HOST}{path}")
        if query:
            url.query = query
        req = build_request("GET", url)
        return req, app.handle(req)

    def test_search_normal_no_xss_event(self):
        app = WebApp()
        _, resp = self._get(app, "/search", {"q": "laptop"})
        assert resp.headers["X-Sim-XSS-Kind"] == "none"
        assert "SIMULATED BROWSER EVENT" not in resp.body

    def test_search_marker_reflected(self):
        app = WebApp()
        _, resp = self._get(app, "/search", {"q": MARKER})
        assert resp.status_code == 200
        assert resp.headers["X-Sim-XSS-Kind"] == "reflected"
        assert resp.headers["X-Sim-XSS-Context"] == "html_text"
        assert MARKER in resp.body
        assert "SIMULATED BROWSER EVENT" in resp.body
        assert "no JavaScript executed" in resp.body

    def test_search_unrecognized_xss_shaped_string_is_normal(self):
        """An arbitrary, realistic-looking XSS payload must never trigger
        a simulated event — only the exact fixed training markers do."""
        app = WebApp()
        for payload in ("<img src=x onerror=alert(1)>", "<svg onload=alert(1)>",
                        "javascript:alert(1)", "<b>bold</b>"):
            _, resp = self._get(app, "/search", {"q": payload})
            assert resp.headers["X-Sim-XSS-Kind"] == "none"
            assert "SIMULATED BROWSER EVENT" not in resp.body

    def test_secure_search_escapes_marker(self):
        app = WebApp()
        _, resp = self._get(app, "/secure-search", {"q": MARKER})
        assert resp.status_code == 200
        assert resp.headers["X-Sim-XSS-Kind"] == "encoded"
        assert "&lt;TRAINING_XSS&gt;" in resp.body
        assert MARKER not in resp.body  # never appears unescaped
        assert "SIMULATED BROWSER EVENT" not in resp.body

    def test_secure_search_normal_input_unaffected(self):
        app = WebApp()
        _, resp = self._get(app, "/secure-search", {"q": "laptop"})
        assert resp.headers["X-Sim-XSS-Kind"] == "none"
        assert "Laptop" in resp.body

    def test_feedback_get_describes_routes(self):
        app = WebApp()
        _, resp = self._get(app, "/feedback")
        assert resp.status_code == 200
        assert "/feedback" in resp.body

    def test_feedback_post_vulnerable_stores_comment_no_immediate_panel(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/feedback")
        req = build_request("POST", url, body=f"name=student&comment={MARKER}")
        resp = app.handle(req)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-XSS-Kind"] == "stored"
        assert "SIMULATED BROWSER EVENT" not in resp.body  # delayed, not immediate
        assert len(app.comments) == 1
        assert app.comments[0].sink == "vulnerable"
        assert app.comments[0].content == MARKER

    def test_feedback_post_normal_comment_no_kind(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/feedback")
        req = build_request("POST", url, body="name=student&comment=Great product!")
        resp = app.handle(req)
        assert resp.headers["X-Sim-XSS-Kind"] == "none"

    def test_secure_feedback_marks_encoded(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/secure-feedback")
        req = build_request("POST", url, body=f"name=student&comment={MARKER}")
        resp = app.handle(req)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-XSS-Kind"] == "encoded"
        assert app.comments[0].sink == "secure"

    def test_comments_get_empty(self):
        app = WebApp()
        _, resp = self._get(app, "/comments")
        assert "no comments yet" in resp.body.lower()
        assert resp.headers["X-Sim-XSS-Kind"] == "none"

    def test_comments_get_renders_vulnerable_comment_with_panel(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/feedback")
        req = build_request("POST", url, body=f"name=student&comment={MARKER}")
        app.handle(req)
        _, resp = self._get(app, "/comments")
        assert resp.headers["X-Sim-XSS-Kind"] == "stored"
        assert MARKER in resp.body
        assert "SIMULATED BROWSER EVENT" in resp.body

    def test_comments_get_renders_secure_comment_escaped(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/secure-feedback")
        req = build_request("POST", url, body=f"name=student&comment={MARKER}")
        app.handle(req)
        _, resp = self._get(app, "/comments")
        assert resp.headers["X-Sim-XSS-Kind"] == "none"  # no vulnerable comment triggered
        assert "&lt;TRAINING_XSS&gt;" in resp.body
        assert "SIMULATED BROWSER EVENT" not in resp.body

    def test_dom_demo_no_input(self):
        app = WebApp()
        _, resp = self._get(app, "/dom-demo")
        assert resp.status_code == 200
        assert resp.headers["X-Sim-XSS-Kind"] == "none"
        assert resp.headers["X-Sim-XSS-Context"] == "dom"
        assert "Source:" in resp.body and "Sink:" in resp.body

    def test_dom_demo_marker_triggers_event(self):
        app = WebApp()
        _, resp = self._get(app, "/dom-demo", {"input": MARKER})
        assert resp.headers["X-Sim-XSS-Kind"] == "dom"
        assert "SIMULATED BROWSER EVENT" in resp.body
        assert "no JavaScript executed" in resp.body

    def test_every_response_carries_csp_header(self):
        app = WebApp()
        for path in ("/", "/products", "/search", "/secure-search", "/comments",
                    "/dom-demo", "/does-not-exist"):
            _, resp = self._get(app, path)
            assert resp.headers.get("Content-Security-Policy") == CSP_POLICY

    def test_csp_not_overridden_by_route_specific_headers(self):
        app = WebApp()
        _, resp = self._get(app, "/search", {"q": MARKER})
        assert resp.headers["Content-Security-Policy"] == CSP_POLICY


# ═══════════════════════════════════════════
# has_xss_marker — pure classification, no execution
# ═══════════════════════════════════════════
class TestHasXssMarker:
    def test_exact_markers_recognized(self):
        for m in TRAINING_XSS_MARKERS:
            assert has_xss_marker(m) is True
            assert has_xss_marker(m.lower()) is True
            assert has_xss_marker(f"  {m}  ") is True

    def test_arbitrary_strings_not_recognized(self):
        for s in ("<img src=x onerror=alert(1)>", "hello", "<TRAINING_XSSX>", ""):
            assert has_xss_marker(s) is False


# ═══════════════════════════════════════════
# XSS state tracking (_track_xss_response via open/forward/repeater)
# ═══════════════════════════════════════════
class TestXssStateTracking:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.web_lab = build_web_lab("xss-investigation")
        return sh

    def test_open_sets_reflected_flag(self):
        sh = self._shell()
        sh.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        assert sh.web_lab.xss.reflected_seen is True
        assert sh.web_lab.xss.dom_seen is False

    def test_open_sets_dom_flag(self):
        sh = self._shell()
        sh.execute(f'open "https://cybershop.training/dom-demo?input={MARKER}"')
        assert sh.web_lab.xss.dom_seen is True

    def test_feedback_and_comments_set_stored_flag(self):
        sh = self._shell()
        sh.execute(f'open -X POST -d "name=student&comment={MARKER}" '
                  "https://cybershop.training/feedback")
        assert sh.web_lab.xss.stored_seen is True  # set on submission already

    def test_secure_search_flag_via_forward(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute(f'open "https://cybershop.training/secure-search?q={MARKER}"')
        assert sh.web_lab.xss.secure_search_tested is False  # queued, not yet handled
        sh.execute("forward")
        assert sh.web_lab.xss.secure_search_tested is True

    def test_secure_feedback_flag_via_repeater_send(self):
        sh = self._shell()
        sh.execute('open -X POST -d "name=student&comment=hi" https://cybershop.training/secure-feedback')
        sh.execute("repeater 1")
        sh.execute(f'edit body "name=student&comment={MARKER}"')
        assert sh.web_lab.xss.secure_feedback_tested is False
        sh.execute("repeater send")
        assert sh.web_lab.xss.secure_feedback_tested is True

    def test_state_survives_save_and_restore(self):
        sh = self._shell()
        sh.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        snapshot = sh.web_lab.to_dict()
        lab2 = build_web_lab("xss-investigation")
        lab2.apply_state(snapshot)
        assert lab2.xss.reflected_seen is True

    def test_comments_persist_through_save_and_restore(self):
        sh = self._shell()
        sh.execute(f'open -X POST -d "name=student&comment={MARKER}" '
                  "https://cybershop.training/feedback")
        snapshot = sh.web_lab.to_dict()
        lab2 = build_web_lab("xss-investigation")
        lab2.apply_state(snapshot)
        assert len(lab2.app.comments) == 1
        assert lab2.app.comments[0].content == MARKER


# ═══════════════════════════════════════════
# Validator — new checks
# ═══════════════════════════════════════════
class TestXssValidatorChecks:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab("xss-investigation")
        return sh

    def _obj(self, check, match="1", **extra):
        v = {"type": "web_state", "check": check, "match": match}
        v.update(extra)
        return {"id": "x", "xp": 10, "validate": v}

    def test_reflected_input(self):
        sh = self._shell()
        obj = self._obj("reflected_input")
        assert not validate(obj, sh).passed
        sh.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        assert validate(obj, sh).passed

    def test_html_context(self):
        sh = self._shell()
        obj = self._obj("html_context", "html_text")
        sh.execute("open https://cybershop.training/search?q=laptop")
        assert validate(obj, sh).passed

    def test_simulated_xss_event(self):
        sh = self._shell()
        obj = self._obj("simulated_xss_event")
        sh.execute("open https://cybershop.training/search?q=laptop")
        assert not validate(obj, sh).passed
        sh.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        assert validate(obj, sh).passed

    def test_stored_input_submitted(self):
        sh = self._shell()
        obj = self._obj("stored_input", "submitted")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -d "name=student&comment={MARKER}" '
                  "https://cybershop.training/feedback")
        assert validate(obj, sh).passed

    def test_stored_input_displayed(self):
        sh = self._shell()
        obj = self._obj("stored_input", "displayed")
        sh.execute(f'open -X POST -d "name=student&comment={MARKER}" '
                  "https://cybershop.training/feedback")
        assert not validate(obj, sh).passed  # submitted, not yet displayed
        sh.execute("open https://cybershop.training/comments")
        assert validate(obj, sh).passed

    def test_reflected_vs_stored_requires_both(self):
        sh = self._shell()
        obj = self._obj("reflected_vs_stored")
        sh.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -d "name=student&comment={MARKER}" '
                  "https://cybershop.training/feedback")
        assert validate(obj, sh).passed

    def test_dom_source(self):
        sh = self._shell()
        obj = self._obj("dom_source")
        assert not validate(obj, sh).passed
        sh.execute("open https://cybershop.training/dom-demo")
        assert validate(obj, sh).passed

    def test_dom_sink(self):
        sh = self._shell()
        obj = self._obj("dom_sink")
        sh.execute("open https://cybershop.training/dom-demo")
        assert not validate(obj, sh).passed
        sh.execute(f'open "https://cybershop.training/dom-demo?input={MARKER}"')
        assert validate(obj, sh).passed

    def test_secure_encoding(self):
        sh = self._shell()
        obj = self._obj("secure_encoding", endpoint="/secure-search")
        assert not validate(obj, sh).passed
        sh.execute(f'open "https://cybershop.training/secure-search?q={MARKER}"')
        assert validate(obj, sh).passed

    def test_html_escaped_observed(self):
        sh = self._shell()
        obj = self._obj("html_escaped_observed")
        sh.execute("open https://cybershop.training/search?q=laptop")
        assert not validate(obj, sh).passed
        sh.execute(f'open "https://cybershop.training/secure-search?q={MARKER}"')
        assert validate(obj, sh).passed

    def test_xss_evidence_collected(self):
        sh = self._shell()
        obj = self._obj("xss_evidence_collected")
        sh.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        sh.execute(f'open -X POST -d "name=student&comment={MARKER}" '
                  "https://cybershop.training/feedback")
        sh.execute(f'open "https://cybershop.training/dom-demo?input={MARKER}"')
        assert not validate(obj, sh).passed
        sh.execute(f'open "https://cybershop.training/secure-search?q={MARKER}"')
        assert validate(obj, sh).passed

    def test_checks_fail_gracefully_without_web_lab(self):
        sh = Shell()
        for check in ("reflected_input", "html_context", "simulated_xss_event",
                      "stored_input", "reflected_vs_stored", "dom_source", "dom_sink",
                      "secure_encoding", "html_escaped_observed", "xss_evidence_collected"):
            assert not validate(self._obj(check), sh).passed

    def test_xss_evidence_collected_does_not_reuse_sqli_evidence_collected(self):
        """Guards against the two missions' capstone checks colliding —
        they must be independently named ('evidence_collected' for SQLi,
        'xss_evidence_collected' for XSS) since they read different
        WebLab sub-states (lab.sqli vs. lab.xss)."""
        sh = self._shell()
        obj = self._obj("evidence_collected")  # the SQLi name, on an XSS lab
        sh.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        # Never passes here: lab.sqli's flags are all still at their
        # untouched defaults for a session that never sent SQLi payloads.
        assert not validate(obj, sh).passed


# ═══════════════════════════════════════════
# Investigation scenario
# ═══════════════════════════════════════════
class TestInvestigationScenario:
    def test_xss_investigation_scenario(self):
        lab = build_web_lab("xss-investigation")
        assert len(lab.investigation_log) == 5

        normal_req, normal_resp = lab.investigation_log[0]
        assert normal_req.path == "/search"
        assert normal_resp.headers["X-Sim-XSS-Kind"] == "none"

        _reflected_req, reflected_resp = lab.investigation_log[1]
        assert reflected_resp.headers["X-Sim-XSS-Kind"] == "reflected"

        stored_req, stored_resp = lab.investigation_log[2]
        assert stored_req.path == "/feedback"
        assert stored_resp.headers["X-Sim-XSS-Kind"] == "stored"

        comments_req, comments_resp = lab.investigation_log[3]
        assert comments_req.path == "/comments"
        assert comments_resp.headers["X-Sim-XSS-Kind"] == "stored"

        secure_req, secure_resp = lab.investigation_log[4]
        assert secure_req.path == "/secure-search"
        assert secure_resp.headers["X-Sim-XSS-Kind"] == "encoded"

    def test_scenario_is_deterministic(self):
        a = build_web_lab("xss-investigation")
        b = build_web_lab("xss-investigation")
        assert a.investigation_log == b.investigation_log

    def test_scenario_never_touches_live_session(self):
        lab = build_web_lab("xss-investigation")
        assert lab.session.history == []
        assert lab.session.cookies == {}
        assert lab.xss.reflected_seen is False
        assert lab.app.comments == []


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "xss-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("xss-fundamentals")
        assert m is not None
        assert m["title"] == "Cross-Site Scripting Fundamentals"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 750

    def test_objective_count(self):
        m = get_mission("xss-fundamentals")
        assert len(m["objectives"]) == 17

    def test_xp_sums_to_total(self):
        m = get_mission("xss-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_every_objective_has_progressive_hints(self):
        m = get_mission("xss-fundamentals")
        for o in m["objectives"]:
            assert "hints" in o
            assert len(o["hints"]) >= 2

    def test_chained_after_sql_injection_fundamentals(self):
        assert MISSIONS["sql-injection-fundamentals"]["next_mission"] == "xss-fundamentals"

    def test_chains_to_csrf_fundamentals(self):
        m = get_mission("xss-fundamentals")
        assert m["next_mission"] == "csrf-fundamentals"

    def test_web_lab_scenario_set(self):
        m = get_mission("xss-fundamentals")
        assert m["web_lab"] == "xss-investigation"

    def test_web_workspace_seeded(self):
        m = get_mission("xss-fundamentals")
        assert "web" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("xss-fundamentals", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 750
        assert sorted(r.progress.completed_ids) == sorted(
            o["id"] for o in r.mission["objectives"])

    def test_no_premature_completion(self):
        r = MissionRunner("xss-fundamentals", 2)
        r.execute("web")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) < len(r.mission["objectives"])

    def test_web_lab_status_carries_xss_fields_and_comments(self):
        r = MissionRunner("xss-fundamentals", 3)
        r.execute(f'open -X POST -d "name=student&comment={MARKER}" '
                 "https://cybershop.training/feedback")
        status = r.web_lab_status()
        assert status["xss"]["stored_seen"] is True
        assert len(status["comments"]) == 1
        assert status["comments"][0]["content"] == MARKER

    def test_ai_context_includes_xss_summary(self):
        r = MissionRunner("xss-fundamentals", 4)
        r.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        ctx = r.ai_context()
        assert ctx["web"]["xss"]["last_xss_kind"] == "reflected"
        assert ctx["web"]["xss"]["reflected_seen"] is True
        assert ctx["web"]["xss"]["dom_seen"] is False

    def test_save_restore_preserves_xss_state(self):
        r = MissionRunner("xss-fundamentals", 5)
        r.execute(f'open "https://cybershop.training/dom-demo?input={MARKER}"')
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.shell.web_lab.xss.dom_seen is True

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("xss-fundamentals", 6)
        r1.execute(f'open "https://cybershop.training/search?q={MARKER}"')
        assert MissionRunner("xss-fundamentals", 7).shell.web_lab.xss.reflected_seen is False


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
        sh.web_lab = build_web_lab("xss-investigation")
        for path in ("/feedback", "/comments", "/dom-demo"):
            out = sh.execute(f"open https://evil.example.com{path}")
            assert out == "External hosts are not available in the training environment."

    def test_no_real_javascript_executed_only_deterministic_text(self):
        """The 'simulated execution' is always fixed text output — never
        eval(), exec(), or any code-execution primitive anywhere in the
        module that produces it."""
        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read()
        for dangerous in ("eval(", "exec(", "compile(", "__import__", "subprocess."):
            assert dangerous not in src

    def test_comments_never_rendered_via_innerhtml_in_browser_js(self):
        """The Comments panel must build DOM nodes with textContent/
        createTextNode, never innerHTML with comment content — otherwise
        a stored marker could become real markup in the actual page."""
        js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static",
                               "labs", "terminal.js")
        with open(js_path, encoding="utf-8") as f:
            js = f.read()
        assert "createTextNode(' ' + c.content)" in js
        assert "commentsEl.innerHTML = ''" in js  # only used to clear, never to inject content

    def test_no_eval_or_dangerous_dom_apis_in_terminal_js_xss_section(self):
        js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static",
                               "labs", "terminal.js")
        with open(js_path, encoding="utf-8") as f:
            js = f.read()
        start = js.index("XSS Fundamentals (YC-035.5)")
        section = js[start:start + 8000]
        for dangerous in ("eval(", "document.write", "Function(", ".innerHTML = c."):
            assert dangerous not in section

    def test_unrecognized_arbitrary_payloads_never_trigger_event(self):
        app = WebApp()
        for payload in ("<script>alert(document.cookie)</script>",
                        "<img src=x onerror=fetch('http://evil.example.com')>",
                        "'; DROP TABLE comments; --"):
            url = parse_url(f"https://{HOST}/search")
            url.query = {"q": payload}
            req = build_request("GET", url)
            resp = app.handle(req)
            assert resp.headers["X-Sim-XSS-Kind"] == "none"

    def test_no_real_credentials_or_secrets_anywhere_in_module(self):
        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read().lower()
        for weak in ("password123", "letmein", "qwerty", "admin@yushacyber.com"):
            assert weak not in src

    def test_xss_state_isolated_between_instances(self):
        lab1 = build_web_lab("xss-investigation")
        lab2 = build_web_lab("xss-investigation")
        url = parse_url(f"https://{HOST}/search")
        url.query = {"q": MARKER}
        lab1.app.handle(build_request("GET", url))
        assert lab1.xss.reflected_seen is False  # app.handle() alone never mutates lab.xss
        assert lab2.xss.reflected_seen is False

    def test_comments_isolated_between_instances(self):
        lab1 = build_web_lab("xss-investigation")
        lab2 = build_web_lab("xss-investigation")
        url = parse_url(f"https://{HOST}/feedback")
        req = build_request("POST", url, body="name=a&comment=b")
        lab1.app.handle(req)
        assert len(lab2.app.comments) == 0


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
        u = User(username="xss_test", email="xss@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "xss_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


SQLI_SOLVE: list[str] = [
    "schema",
    "web",
    "open https://cybershop.training/search?q=laptop",
    "intercept on",
    "open https://cybershop.training/search?q=keyboard",
    "forward",
    "intercept off",
    "open \"https://cybershop.training/search?q='\"",
    "open \"https://cybershop.training/search?q=' OR '1'='1\"",
    "open \"https://cybershop.training/search?q=' AND '1'='2\"",
    "compare 1 2",
    "query",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/training-login',
    "open -X POST -d \"username=admin'--&password=x\" https://cybershop.training/training-login",
    "open \"https://cybershop.training/secure-search?q=' OR '1'='1\"",
    "evidence", "inspect 1", "inspect 2", "inspect 3", "inspect 4",
    ('echo "Conclusion: unsafe string concatenation let the TRUE and FALSE training '
     "conditions change the search query's own logic - this is SQL injection. The "
     "secure endpoint returned a normal, unaffected result for the same input because "
     'parameterized queries keep input as data, never as query syntax." > '
     'web/sqli-investigation.txt'),
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

            assert mission_status(uid, "xss-fundamentals") == "locked"

            start_mission(uid, "sql-injection-fundamentals")
            for c in SQLI_SOLVE:
                execute_command(uid, "sql-injection-fundamentals", c)

            assert mission_status(uid, "xss-fundamentals") == "available"

            start_mission(uid, "xss-fundamentals")
            for c in SOLVE:
                execute_command(uid, "xss-fundamentals", c)

            assert mission_status(uid, "xss-fundamentals") == "completed"

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
            assert "xss-fundamentals" in ids

    def test_terminal_page_shows_xss_panels(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/xss-fundamentals")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "data-xss-badges" in body
            assert "data-xss-search-vuln" in body
            assert "data-xss-search-secure" in body
            assert "data-xss-feedback-vuln" in body
            assert "data-xss-dom-open" in body
            assert "data-xss-flow-step" in body
            assert "data-xss-compare-run" in body
            assert "data-xss-csp" in body
            # Proxy Control (reused from YC-035.2) also present for this mission.
            assert "data-proxy-badge" in body
            # Inspector (reused from YC-035.1) still present too.
            assert "data-inspector-toggle" in body

    def test_xss_panel_not_shown_on_other_missions(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/sql-injection-fundamentals")
            assert "data-xss-badges" not in r.data.decode("utf-8")
            r2 = c.get("/terminal/mission/burp-fundamentals")
            assert "data-xss-badges" not in r2.data.decode("utf-8")

    def test_execute_returns_xss_state(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/xss-fundamentals")
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "xss-fundamentals",
                "command": f'open "https://cybershop.training/search?q={MARKER}"',
            })
            assert r.status_code == 200
            d = r.get_json()
            assert d["web_lab_status"]["xss"]["reflected_seen"] is True

    def test_hint_endpoint_returns_progressive_hints(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/xss-fundamentals")
            r1 = c.post("/api/terminal/mission/hint", json={
                "slug": "xss-fundamentals", "objective_id": "xs-1"})
            r2 = c.post("/api/terminal/mission/hint", json={
                "slug": "xss-fundamentals", "objective_id": "xs-1"})
            assert r1.status_code == 200 and r2.status_code == 200
            assert r1.get_json()["hint"] != r2.get_json()["hint"]
