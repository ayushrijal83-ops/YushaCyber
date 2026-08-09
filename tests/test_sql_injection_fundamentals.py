"""Tests for YC-035.4 — SQL Injection Fundamentals interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0354-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_si.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell
from app.core.terminal.web import (
    DB_SCHEMA,
    HOST,
    PRODUCTS,
    TRAINING_AUTH_BYPASS_USERNAME,
    TRAINING_ERROR_PAYLOAD,
    TRAINING_FALSE_PAYLOAD,
    TRAINING_TRUE_PAYLOAD,
    WebApp,
    build_request,
    build_web_lab,
    parse_url,
)

SOLVE: list[str] = [
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


# ═══════════════════════════════════════════
# WebApp routing — new routes
# ═══════════════════════════════════════════
class TestWebAppRouting:
    def _search(self, app, q):
        url = parse_url(f"https://{HOST}/search")
        url.query = {"q": q}
        req = build_request("GET", url)
        return req, app.handle(req)

    def _secure_search(self, app, q):
        url = parse_url(f"https://{HOST}/secure-search")
        url.query = {"q": q}
        req = build_request("GET", url)
        return req, app.handle(req)

    def test_normal_search_matches_catalog(self):
        app = WebApp()
        _, resp = self._search(app, "laptop")
        assert resp.status_code == 200
        assert "Laptop" in resp.body
        assert resp.headers["X-Sim-Query-Kind"] == "normal"

    def test_normal_search_no_match(self):
        app = WebApp()
        _, resp = self._search(app, "nonexistent-item")
        assert resp.status_code == 200
        assert "0 match" in resp.body

    def test_boolean_true_returns_every_product(self):
        app = WebApp()
        _, resp = self._search(app, TRAINING_TRUE_PAYLOAD)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Query-Kind"] == "boolean_true"
        for p in PRODUCTS:
            assert p["name"] in resp.body

    def test_boolean_false_returns_nothing(self):
        app = WebApp()
        _, resp = self._search(app, TRAINING_FALSE_PAYLOAD)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Query-Kind"] == "boolean_false"
        assert "0 match" in resp.body

    def test_malformed_quote_returns_500(self):
        app = WebApp()
        _, resp = self._search(app, TRAINING_ERROR_PAYLOAD)
        assert resp.status_code == 500
        assert resp.headers["X-Sim-Query-Kind"] == "error"
        assert "Database error" in resp.body

    def test_union_pattern_never_leaks_data(self):
        app = WebApp()
        _, resp = self._search(app, "' UNION SELECT NULL, NULL --")
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Query-Kind"] == "union"
        assert "0 match" in resp.body
        for u in ("admin", "student", "analyst"):
            assert u not in resp.body

    def test_query_representation_shows_structural_change(self):
        app = WebApp()
        _, resp = self._search(app, TRAINING_TRUE_PAYLOAD)
        assert resp.headers["X-Sim-Query"] == f"SELECT * FROM products WHERE name = '{TRAINING_TRUE_PAYLOAD}'"

    def test_secure_search_ignores_injection_semantics(self):
        app = WebApp()
        _, resp = self._secure_search(app, TRAINING_TRUE_PAYLOAD)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Query-Kind"] == "parameterized"
        assert "0 match" in resp.body  # no literal product named "' OR '1'='1"

    def test_secure_search_query_representation_never_changes(self):
        app = WebApp()
        for q in ("laptop", TRAINING_TRUE_PAYLOAD, TRAINING_ERROR_PAYLOAD, "' UNION SELECT NULL --"):
            _, resp = self._secure_search(app, q)
            assert resp.headers["X-Sim-Query"] == "SELECT * FROM products WHERE name = ?"

    def test_secure_search_normal_keyword_still_matches(self):
        app = WebApp()
        _, resp = self._secure_search(app, "laptop")
        assert "Laptop" in resp.body

    def test_training_login_normal_credentials(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/training-login")
        req = build_request("POST", url, body="username=student&password=training123")
        resp = app.handle(req)
        assert resp.status_code == 200
        assert '"authenticated_as": "student"' in resp.body

    def test_training_login_wrong_password_401(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/training-login")
        req = build_request("POST", url, body="username=student&password=wrong")
        resp = app.handle(req)
        assert resp.status_code == 401
        assert resp.headers["X-Sim-Query-Kind"] == "normal"

    def test_training_login_bypass_authenticates_as_admin(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/training-login")
        req = build_request("POST", url,
                            body=f"username={TRAINING_AUTH_BYPASS_USERNAME}&password=anything")
        resp = app.handle(req)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Query-Kind"] == "auth_bypass"
        assert '"authenticated_as": "admin"' in resp.body

    def test_training_login_bypass_query_repr_shows_comment(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/training-login")
        req = build_request("POST", url,
                            body=f"username={TRAINING_AUTH_BYPASS_USERNAME}&password=anything")
        resp = app.handle(req)
        assert "--" in resp.headers["X-Sim-Query"]

    def test_secure_login_rejects_bypass_payload(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/secure-login")
        req = build_request("POST", url,
                            body=f"username={TRAINING_AUTH_BYPASS_USERNAME}&password=anything")
        resp = app.handle(req)
        assert resp.status_code == 401
        assert resp.headers["X-Sim-Query-Kind"] == "parameterized"

    def test_secure_login_normal_credentials_still_work(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/secure-login")
        req = build_request("POST", url, body="username=student&password=training123")
        resp = app.handle(req)
        assert resp.status_code == 200


# ═══════════════════════════════════════════
# Terminal commands — 'schema' and 'query'
# ═══════════════════════════════════════════
class TestSchemaCommand:
    def test_no_lab_needed_static(self):
        sh = Shell()
        out = sh.execute("schema")
        assert "users:" in out
        assert "products:" in out

    def test_single_table(self):
        sh = Shell()
        out = sh.execute("schema products")
        assert "name (TEXT)" in out
        assert "users:" not in out

    def test_unknown_table(self):
        sh = Shell()
        out = sh.execute("schema nope")
        assert "unknown table" in out


class TestQueryVisualizerCommand:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.web_lab = build_web_lab("sqli-investigation")
        return sh

    def test_no_lab_configured(self):
        sh = Shell()
        assert "no simulated web environment" in sh.execute("query")

    def test_no_request_yet(self):
        sh = self._shell()
        assert "No request made yet" in sh.execute("query")

    def test_query_after_search_increments_counter(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/search?q=laptop")
        out = sh.execute("query")
        assert "Application Query" in out
        assert sh.web_lab.sqli.query_inspections == 1
        sh.execute("query")
        assert sh.web_lab.sqli.query_inspections == 2

    def test_query_on_unrelated_route_has_no_representation(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/products")
        out = sh.execute("query")
        assert "no simulated query representation" in out


# ═══════════════════════════════════════════
# sqli evidence tracking (_track_sqli_response via open/forward/repeater)
# ═══════════════════════════════════════════
class TestSqliStateTracking:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.web_lab = build_web_lab("sqli-investigation")
        return sh

    def test_open_sets_boolean_flags(self):
        sh = self._shell()
        sh.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        assert sh.web_lab.sqli.boolean_true_seen is True
        assert sh.web_lab.sqli.boolean_false_seen is False
        sh.execute("open \"https://cybershop.training/search?q=' AND '1'='2\"")
        assert sh.web_lab.sqli.boolean_false_seen is True

    def test_secure_search_flag_via_forward(self):
        sh = self._shell()
        sh.execute("intercept on")
        sh.execute("open \"https://cybershop.training/secure-search?q=' OR '1'='1\"")
        assert sh.web_lab.sqli.secure_search_tested is False  # queued, not yet handled
        sh.execute("forward")
        assert sh.web_lab.sqli.secure_search_tested is True

    def test_auth_bypass_flag_via_repeater_send(self):
        sh = self._shell()
        sh.execute("open -X POST -d \"username=admin'--&password=x\" "
                  "https://cybershop.training/training-login")
        assert sh.web_lab.sqli.auth_bypass_triggered is True
        sh2 = self._shell()
        sh2.execute("open -X POST -d \"username=student&password=training123\" "
                   "https://cybershop.training/training-login")
        sh2.execute("repeater 1")
        sh2.execute("edit body \"username=admin'--&password=x\"")
        assert sh2.web_lab.sqli.auth_bypass_triggered is False
        sh2.execute("repeater send")
        assert sh2.web_lab.sqli.auth_bypass_triggered is True

    def test_state_survives_save_and_restore(self):
        sh = self._shell()
        sh.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        snapshot = sh.web_lab.to_dict()
        lab2 = build_web_lab("sqli-investigation")
        lab2.apply_state(snapshot)
        assert lab2.sqli.boolean_true_seen is True


# ═══════════════════════════════════════════
# Validator — new checks
# ═══════════════════════════════════════════
class TestSqliValidatorChecks:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab("sqli-investigation")
        return sh

    def _obj(self, check, match="1", **extra):
        v = {"type": "web_state", "check": check, "match": match}
        v.update(extra)
        return {"id": "x", "xp": 10, "validate": v}

    def test_normal_request(self):
        sh = self._shell()
        obj = self._obj("normal_request", "laptop", param="q")
        assert not validate(obj, sh).passed
        sh.execute("open https://cybershop.training/search?q=laptop")
        assert validate(obj, sh).passed

    def test_error_observed(self):
        sh = self._shell()
        obj = self._obj("error_observed")
        assert not validate(obj, sh).passed
        sh.execute("open \"https://cybershop.training/search?q='\"")
        assert validate(obj, sh).passed

    def test_boolean_true_observed(self):
        sh = self._shell()
        obj = self._obj("boolean_true_observed")
        assert not validate(obj, sh).passed
        sh.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        assert validate(obj, sh).passed

    def test_boolean_false_observed(self):
        sh = self._shell()
        obj = self._obj("boolean_false_observed")
        sh.execute("open \"https://cybershop.training/search?q=' AND '1'='2\"")
        assert validate(obj, sh).passed

    def test_response_difference_requires_both(self):
        sh = self._shell()
        obj = self._obj("response_difference")
        sh.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        assert not validate(obj, sh).passed
        sh.execute("open \"https://cybershop.training/search?q=' AND '1'='2\"")
        assert validate(obj, sh).passed

    def test_query_structure_inspected(self):
        sh = self._shell()
        obj = self._obj("query_structure_inspected")
        sh.execute("open https://cybershop.training/search?q=laptop")
        assert not validate(obj, sh).passed
        sh.execute("query")
        assert validate(obj, sh).passed

    def test_training_auth_scenario_opened(self):
        sh = self._shell()
        obj = self._obj("training_auth_scenario", "opened")
        assert not validate(obj, sh).passed
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/training-login')
        assert validate(obj, sh).passed

    def test_training_auth_scenario_bypassed(self):
        sh = self._shell()
        obj = self._obj("training_auth_scenario", "bypassed")
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/training-login')
        assert not validate(obj, sh).passed
        sh.execute("open -X POST -d \"username=admin'--&password=x\" "
                  "https://cybershop.training/training-login")
        assert validate(obj, sh).passed

    def test_secure_endpoint_tested(self):
        sh = self._shell()
        obj = self._obj("secure_endpoint_tested", endpoint="/secure-search")
        assert not validate(obj, sh).passed
        sh.execute("open \"https://cybershop.training/secure-search?q=' OR '1'='1\"")
        assert validate(obj, sh).passed

    def test_parameterized_query_identified(self):
        sh = self._shell()
        obj = self._obj("parameterized_query_identified")
        sh.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        assert not validate(obj, sh).passed
        sh.execute("open \"https://cybershop.training/secure-search?q=' OR '1'='1\"")
        assert validate(obj, sh).passed

    def test_evidence_collected_requires_all_four(self):
        sh = self._shell()
        obj = self._obj("evidence_collected")
        sh.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        sh.execute("open \"https://cybershop.training/search?q=' AND '1'='2\"")
        sh.execute("query")
        assert not validate(obj, sh).passed
        sh.execute("open \"https://cybershop.training/secure-search?q=' OR '1'='1\"")
        assert validate(obj, sh).passed

    def test_checks_fail_gracefully_without_web_lab(self):
        sh = Shell()
        for check in ("normal_request", "error_observed", "boolean_true_observed",
                      "boolean_false_observed", "response_difference",
                      "query_structure_inspected", "training_auth_scenario",
                      "secure_endpoint_tested", "parameterized_query_identified",
                      "evidence_collected"):
            assert not validate(self._obj(check), sh).passed


# ═══════════════════════════════════════════
# Investigation scenario
# ═══════════════════════════════════════════
class TestInvestigationScenario:
    def test_sqli_investigation_scenario(self):
        lab = build_web_lab("sqli-investigation")
        assert len(lab.investigation_log) == 4
        normal_req, normal_resp = lab.investigation_log[0]
        assert normal_req.path == "/search"
        assert normal_resp.headers["X-Sim-Query-Kind"] == "normal"

        _true_req, true_resp = lab.investigation_log[1]
        assert true_resp.headers["X-Sim-Query-Kind"] == "boolean_true"

        _false_req, false_resp = lab.investigation_log[2]
        assert false_resp.headers["X-Sim-Query-Kind"] == "boolean_false"

        secure_req, secure_resp = lab.investigation_log[3]
        assert secure_req.path == "/secure-search"
        assert secure_resp.headers["X-Sim-Query-Kind"] == "parameterized"

    def test_scenario_is_deterministic(self):
        a = build_web_lab("sqli-investigation")
        b = build_web_lab("sqli-investigation")
        assert a.investigation_log == b.investigation_log

    def test_scenario_never_touches_live_session(self):
        lab = build_web_lab("sqli-investigation")
        assert lab.session.history == []
        assert lab.session.cookies == {}
        assert lab.sqli.boolean_true_seen is False


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "sql-injection-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("sql-injection-fundamentals")
        assert m is not None
        assert m["title"] == "SQL Injection Fundamentals"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 700

    def test_objective_count(self):
        m = get_mission("sql-injection-fundamentals")
        assert len(m["objectives"]) == 16

    def test_xp_sums_to_total(self):
        m = get_mission("sql-injection-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_every_objective_has_progressive_hints(self):
        m = get_mission("sql-injection-fundamentals")
        for o in m["objectives"]:
            assert "hints" in o
            assert len(o["hints"]) >= 2

    def test_chained_after_authentication_sessions(self):
        assert MISSIONS["authentication-sessions"]["next_mission"] == "sql-injection-fundamentals"

    def test_chains_to_xss_fundamentals(self):
        # Chained after this mission by YC-035.5 — see
        # docs/XSS_FUNDAMENTALS.md.
        m = get_mission("sql-injection-fundamentals")
        assert m["next_mission"] == "xss-fundamentals"

    def test_web_lab_scenario_set(self):
        m = get_mission("sql-injection-fundamentals")
        assert m["web_lab"] == "sqli-investigation"

    def test_web_workspace_seeded(self):
        m = get_mission("sql-injection-fundamentals")
        assert "web" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("sql-injection-fundamentals", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 700
        assert sorted(r.progress.completed_ids) == sorted(
            o["id"] for o in r.mission["objectives"])

    def test_no_premature_completion(self):
        r = MissionRunner("sql-injection-fundamentals", 2)
        r.execute("schema")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) < len(r.mission["objectives"])

    def test_web_lab_status_carries_sqli_fields(self):
        r = MissionRunner("sql-injection-fundamentals", 3)
        r.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        status = r.web_lab_status()
        assert status["sqli"]["boolean_true_seen"] is True
        assert status["db_schema"] == DB_SCHEMA

    def test_ai_context_includes_injection_summary(self):
        r = MissionRunner("sql-injection-fundamentals", 4)
        r.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        ctx = r.ai_context()
        assert ctx["web"]["injection"]["last_query_kind"] == "boolean_true"
        assert ctx["web"]["injection"]["boolean_true_observed"] is True
        assert ctx["web"]["injection"]["auth_bypass_triggered"] is False

    def test_save_restore_preserves_sqli_state(self):
        r = MissionRunner("sql-injection-fundamentals", 5)
        r.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        r.execute("query")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.shell.web_lab.sqli.boolean_true_seen is True
        assert r2.shell.web_lab.sqli.query_inspections == 1

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("sql-injection-fundamentals", 6)
        r1.execute("open \"https://cybershop.training/search?q=' OR '1'='1\"")
        assert MissionRunner("sql-injection-fundamentals", 7).shell.web_lab.sqli.boolean_true_seen is False


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
        sh.web_lab = build_web_lab("sqli-investigation")
        for path in ("/search?q=laptop", "/secure-search?q=laptop"):
            out = sh.execute(f"open https://evil.example.com{path}")
            assert out == "External hosts are not available in the training environment."
        out = sh.execute('open -X POST -d "username=admin&password=x" '
                         'https://evil.example.com/training-login')
        assert out == "External hosts are not available in the training environment."

    def test_no_arbitrary_sql_execution_only_fixed_patterns(self):
        """An unrecognized, arbitrary 'SQL-shaped' string must fall through
        to being treated as a plain, literal (safe) search term — never a
        special outcome. This is the core safety property: only the
        handful of *exact* training payloads are recognized."""
        app = WebApp()
        for arbitrary in ("DROP TABLE users;", "1; DELETE FROM products", "'; --",
                         "SELECT * FROM users", "' OR 1=1 --", "random garbage input"):
            url = parse_url(f"https://{HOST}/search")
            url.query = {"q": arbitrary}
            req = build_request("GET", url)
            resp = app.handle(req)
            assert resp.headers["X-Sim-Query-Kind"] == "normal"
            assert resp.status_code == 200

    def test_no_real_credentials_or_pii_anywhere_in_module(self):
        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read().lower()
        assert "training123" in src
        for weak in ("password123", "letmein", "qwerty", "admin@yushacyber.com"):
            assert weak not in src

    def test_schema_command_never_returns_row_data(self):
        sh = Shell()
        out = sh.execute("schema")
        # Structure only — no fictional row values (e.g. "student", "admin"
        # as *data*) should ever appear in the schema output itself.
        assert "INTEGER" in out or "TEXT" in out
        assert "training123" not in out

    def test_sqli_state_isolated_between_instances(self):
        lab1 = build_web_lab("sqli-investigation")
        lab2 = build_web_lab("sqli-investigation")
        url = parse_url(f"https://{HOST}/search")
        url.query = {"q": TRAINING_TRUE_PAYLOAD}
        lab1.app.handle(build_request("GET", url))
        assert lab1.sqli.boolean_true_seen is False  # app.handle() alone never mutates lab.sqli
        assert lab2.sqli.boolean_true_seen is False


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
        u = User(username="si_test", email="sqli@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "si_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


AUTH_SOLVE: list[str] = [
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

            assert mission_status(uid, "sql-injection-fundamentals") == "locked"

            start_mission(uid, "authentication-sessions")
            for c in AUTH_SOLVE:
                execute_command(uid, "authentication-sessions", c)

            assert mission_status(uid, "sql-injection-fundamentals") == "available"

            start_mission(uid, "sql-injection-fundamentals")
            for c in SOLVE:
                execute_command(uid, "sql-injection-fundamentals", c)

            assert mission_status(uid, "sql-injection-fundamentals") == "completed"

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
            assert "sql-injection-fundamentals" in ids

    def test_terminal_page_shows_sqli_panels(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/sql-injection-fundamentals")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "data-sqli-badges" in body
            assert "data-sqli-search-vuln" in body
            assert "data-sqli-search-secure" in body
            assert "data-sqli-login-vuln" in body
            assert "data-sqli-login-bypass" in body
            assert "data-sqli-schema" in body
            assert "data-sqli-qv-query" in body
            assert "data-sqli-compare-run" in body
            # Proxy Control (reused from YC-035.2) also present for this mission.
            assert "data-proxy-badge" in body
            # Inspector (reused from YC-035.1) still present too.
            assert "data-inspector-toggle" in body

    def test_sqli_panel_not_shown_on_other_missions(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/burp-fundamentals")
            body = r.data.decode("utf-8")
            assert "data-sqli-badges" not in body
            r2 = c.get("/terminal/mission/authentication-sessions")
            assert "data-sqli-badges" not in r2.data.decode("utf-8")

    def test_execute_returns_sqli_state(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/sql-injection-fundamentals")
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "sql-injection-fundamentals",
                "command": "open \"https://cybershop.training/search?q=' OR '1'='1\"",
            })
            assert r.status_code == 200
            d = r.get_json()
            assert d["web_lab_status"]["sqli"]["boolean_true_seen"] is True

    def test_hint_endpoint_returns_progressive_hints(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/sql-injection-fundamentals")
            r1 = c.post("/api/terminal/mission/hint", json={
                "slug": "sql-injection-fundamentals", "objective_id": "si-1"})
            r2 = c.post("/api/terminal/mission/hint", json={
                "slug": "sql-injection-fundamentals", "objective_id": "si-1"})
            assert r1.status_code == 200 and r2.status_code == 200
            assert r1.get_json()["hint"] != r2.get_json()["hint"]
