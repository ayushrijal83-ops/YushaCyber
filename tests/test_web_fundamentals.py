"""Tests for YC-035.0 — Web Fundamentals interactive mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0350-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_web.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell
from app.core.terminal.web import HOST, build_request, build_web_lab, parse_url

SOLVE: list[str] = [
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


# ═══════════════════════════════════════════
# URL parsing
# ═══════════════════════════════════════════
class TestUrlParsing:
    def test_full_url(self):
        u = parse_url("https://cybershop.training:443/products?id=42")
        assert u.scheme == "https"
        assert u.host == "cybershop.training"
        assert u.port == 443
        assert u.path == "/products"
        assert u.query == {"id": "42"}

    def test_default_https_port(self):
        u = parse_url("https://cybershop.training/")
        assert u.port == 443

    def test_default_http_port(self):
        u = parse_url("http://cybershop.training/")
        assert u.port == 80

    def test_no_query(self):
        u = parse_url("https://cybershop.training/products")
        assert u.query == {}

    def test_multiple_query_params(self):
        u = parse_url("https://cybershop.training/search?q=linux&page=2")
        assert u.query == {"q": "linux", "page": "2"}

    def test_fragment(self):
        u = parse_url("https://cybershop.training/products#reviews")
        assert u.fragment == "reviews"


# ═══════════════════════════════════════════
# WebApp routing
# ═══════════════════════════════════════════
class TestWebAppRouting:
    def _get(self, app, path, cookies=None):
        url = parse_url(f"https://{HOST}{path}")
        req = build_request("GET", url, cookies=cookies)
        return req, app.handle(req)

    def test_home_200(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        _, resp = self._get(app, "/")
        assert resp.status_code == 200

    def test_products_no_id(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        _, resp = self._get(app, "/products")
        assert resp.status_code == 200
        assert "catalog" in resp.body.lower()

    def test_products_with_id(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        url = parse_url(f"https://{HOST}/products?id=42")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert "42" in resp.body

    def test_search_echoes_query(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        url = parse_url(f"https://{HOST}/search?q=linux")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert "linux" in resp.body

    def test_404_for_unknown_route(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        _, resp = self._get(app, "/does-not-exist")
        assert resp.status_code == 404

    def test_login_get_redirects(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        _, resp = self._get(app, "/login")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/auth/login"

    def test_auth_login_page(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        _, resp = self._get(app, "/auth/login")
        assert resp.status_code == 200

    def test_login_post_valid_credentials(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        url = parse_url(f"https://{HOST}/login")
        req = build_request("POST", url, body="username=student&password=training123")
        resp = app.handle(req)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/profile"
        assert resp.cookies["session_id"] == "student-session"

    def test_login_post_invalid_credentials(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        url = parse_url(f"https://{HOST}/login")
        req = build_request("POST", url, body="username=student&password=wrong")
        resp = app.handle(req)
        assert resp.status_code == 401

    def test_profile_requires_session(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        _, resp = self._get(app, "/profile")
        assert resp.status_code == 401

    def test_profile_with_valid_session(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        login_url = parse_url(f"https://{HOST}/login")
        login_req = build_request("POST", login_url, body="username=student&password=training123")
        login_resp = app.handle(login_req)
        sid = login_resp.cookies["session_id"]
        _, resp = self._get(app, "/profile", cookies={"session_id": sid})
        assert resp.status_code == 200
        assert "student" in resp.body

    def test_logout_clears_session(self):
        from app.core.terminal.web import WebApp
        app = WebApp()
        login_url = parse_url(f"https://{HOST}/login")
        login_req = build_request("POST", login_url, body="username=student&password=training123")
        login_resp = app.handle(login_req)
        sid = login_resp.cookies["session_id"]
        self._get(app, "/logout", cookies={"session_id": sid})
        assert sid not in app.sessions


# ═══════════════════════════════════════════
# Web commands (terminal)
# ═══════════════════════════════════════════
class TestWebCommands:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.web_lab = build_web_lab()
        return sh

    def test_no_lab_configured(self):
        sh = Shell()
        assert "no simulated web environment" in sh.execute("open https://cybershop.training/")
        assert "no simulated web environment" in sh.execute("web")

    def test_open_get(self):
        sh = self._shell()
        out = sh.execute("open https://cybershop.training/products?id=42")
        assert "GET /products?id=42" in out
        assert "200 OK" in out

    def test_open_rejects_external_host(self):
        sh = self._shell()
        out = sh.execute("open https://google.com/")
        assert out == "External hosts are not available in the training environment."

    def test_open_no_url(self):
        sh = self._shell()
        assert "Usage: open" in sh.execute("open")

    def test_request_convenience_command(self):
        sh = self._shell()
        out = sh.execute("request GET /products")
        assert "GET /products" in out

    def test_request_missing_args(self):
        sh = self._shell()
        assert "Usage: request" in sh.execute("request GET")

    def test_post_with_data(self):
        sh = self._shell()
        out = sh.execute(
            'open -X POST -d "username=student&password=training123" '
            'https://cybershop.training/login')
        assert "POST /login" in out
        assert "302 Found" in out
        assert "Set-Cookie: session_id=student-session" in out

    def test_cookie_jar_used_on_subsequent_requests(self):
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        out = sh.execute("open https://cybershop.training/profile")
        assert "Cookie: session_id=student-session" in out
        assert "200 OK" in out

    def test_web_overview_shows_login_state(self):
        sh = self._shell()
        assert "Not logged in" in sh.execute("web")
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        assert "Logged in as student" in sh.execute("web")

    def test_headers_no_request_yet(self):
        sh = self._shell()
        assert "No request made yet" in sh.execute("headers")

    def test_headers_shows_both_sections(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/")
        out = sh.execute("headers")
        assert "Request headers:" in out
        assert "Response headers:" in out

    def test_cookies_empty(self):
        sh = self._shell()
        assert "No cookies stored" in sh.execute("cookies")

    def test_cookies_after_login(self):
        sh = self._shell()
        sh.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        out = sh.execute("cookies")
        assert "session_id=student-session" in out

    def test_response_command(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/")
        out = sh.execute("response")
        assert "200 OK" in out
        assert "GET" not in out.split("\n")[0]  # response view, not the request line

    def test_evidence_lists_investigation_log(self):
        sh = self._shell()
        out = sh.execute("evidence")
        assert "#1" in out and "#2" in out and "#3" in out
        assert "/profile" in out

    def test_inspect_evidence_entry(self):
        sh = self._shell()
        out = sh.execute("inspect 3")
        assert "GET /profile" in out
        assert "401 Unauthorized" in out

    def test_inspect_unknown_evidence_entry(self):
        sh = self._shell()
        assert "not found" in sh.execute("inspect 99")

    def test_inspect_last_request_when_no_number(self):
        sh = self._shell()
        sh.execute("open https://cybershop.training/")
        out = sh.execute("inspect")
        assert "GET /" in out


# ═══════════════════════════════════════════
# Validator — web_state
# ═══════════════════════════════════════════
class TestWebStateValidator:
    def _shell_with_request(self, method="GET", path="/", body="", query=None):
        sh = Shell()
        sh.web_lab = build_web_lab()
        url = parse_url(f"https://{HOST}{path}" + (f"?{'&'.join(f'{k}={v}' for k, v in (query or {}).items())}" if query else ""))
        req = build_request(method, url, body=body, cookies=sh.web_lab.session.cookies)
        resp = sh.web_lab.app.handle(req)
        sh.web_lab.session.record(req, resp)
        return sh

    def test_status_code_pass(self):
        sh = self._shell_with_request(path="/")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "status_code", "match": "200"}}
        assert validate(obj, sh).passed

    def test_status_code_fail(self):
        sh = self._shell_with_request(path="/")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "status_code", "match": "404"}}
        assert not validate(obj, sh).passed

    def test_method_check(self):
        sh = self._shell_with_request(method="POST", path="/login", body="username=student&password=training123")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "method", "match": "POST"}}
        assert validate(obj, sh).passed

    def test_path_check(self):
        sh = self._shell_with_request(path="/products")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "path", "match": "/products"}}
        assert validate(obj, sh).passed

    def test_query_param_check(self):
        sh = self._shell_with_request(path="/products", query={"id": "42"})
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "query_param",
                                                  "param": "id", "match": "42"}}
        assert validate(obj, sh).passed

    def test_header_request_check(self):
        sh = self._shell_with_request(path="/")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "header",
                                                  "in": "request", "header": "Host",
                                                  "match": "cybershop.training"}}
        assert validate(obj, sh).passed

    def test_header_response_check(self):
        sh = self._shell_with_request(path="/")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "header",
                                                  "in": "response", "header": "Content-Type",
                                                  "match": "text/html"}}
        assert validate(obj, sh).passed

    def test_redirect_location_check(self):
        sh = self._shell_with_request(path="/login")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "redirect_location",
                                                  "match": "/auth/login"}}
        assert validate(obj, sh).passed

    def test_redirect_location_not_satisfied_by_visiting_destination(self):
        sh = self._shell_with_request(path="/auth/login")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "redirect_location",
                                                  "match": "/auth/login"}}
        assert not validate(obj, sh).passed

    def test_cookie_check(self):
        sh = self._shell_with_request(method="POST", path="/login",
                                      body="username=student&password=training123")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "cookie",
                                                  "cookie_name": "session_id",
                                                  "match": "student-session"}}
        assert validate(obj, sh).passed

    def test_session_authenticated_requires_actual_protected_access(self):
        sh = self._shell_with_request(method="POST", path="/login",
                                      body="username=student&password=training123")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state",
                                                  "check": "session_authenticated", "match": "true"}}
        assert not validate(obj, sh).passed  # logged in, but /profile never requested

    def test_session_authenticated_passes_after_profile_access(self):
        sh = Shell()
        sh.web_lab = build_web_lab()
        # login
        url = parse_url(f"https://{HOST}/login")
        req = build_request("POST", url, body="username=student&password=training123",
                            cookies=sh.web_lab.session.cookies)
        resp = sh.web_lab.app.handle(req)
        sh.web_lab.session.record(req, resp)
        # then actually hit /profile with the cookie
        url2 = parse_url(f"https://{HOST}/profile")
        req2 = build_request("GET", url2, cookies=sh.web_lab.session.cookies)
        resp2 = sh.web_lab.app.handle(req2)
        sh.web_lab.session.record(req2, resp2)
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state",
                                                  "check": "session_authenticated", "match": "true"}}
        assert validate(obj, sh).passed

    def test_no_web_lab_configured(self):
        sh = Shell()
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "status_code", "match": "200"}}
        assert not validate(obj, sh).passed

    def test_unknown_check(self):
        sh = self._shell_with_request(path="/")
        obj = {"id": "x", "xp": 10, "validate": {"type": "web_state", "check": "bogus", "match": "x"}}
        assert not validate(obj, sh).passed


# ═══════════════════════════════════════════
# Security isolation — structural, not just behavioral
# ═══════════════════════════════════════════
class TestSecurityIsolation:
    def test_web_module_has_no_network_capable_imports(self):
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
        # urllib.parse (pure string parsing) is expected and fine.
        assert any(m == "urllib.parse" or m.startswith("urllib.parse")
                  for m in imported_modules)

    def test_web_command_handlers_have_no_shell_execution(self):
        import inspect

        from app.core.terminal import commands as cmdmod
        for fn in (cmdmod._open, cmdmod._request, cmdmod._web, cmdmod._evidence,
                  cmdmod._inspect, cmdmod._web_headers, cmdmod._web_cookies,
                  cmdmod._web_response):
            src = inspect.getsource(fn)
            body = src.split('"""', 2)[-1] if '"""' in src else src
            for forbidden in ("subprocess.", "os.system(", "os.popen(", "shell=True",
                              "Popen(", "eval(", "exec(", "socket.", "requests."):
                assert forbidden not in body, f"{fn.__name__} contains {forbidden!r}"

    def test_external_host_rejected_before_any_request_object_exists(self):
        sh = Shell()
        sh.web_lab = build_web_lab()
        out = sh.execute("open https://google.com/")
        assert out == "External hosts are not available in the training environment."
        assert sh.web_lab.session.last_request is None  # no request was ever recorded

    def test_investigation_log_is_deterministic(self):
        lab_a = build_web_lab()
        lab_b = build_web_lab()
        assert lab_a.investigation_log == lab_b.investigation_log

    def test_no_random_credentials_or_responses(self):
        # Same credentials -> same session id, every time.
        from app.core.terminal.web import WebApp
        app1, app2 = WebApp(), WebApp()
        url = parse_url(f"https://{HOST}/login")
        req1 = build_request("POST", url, body="username=student&password=training123")
        req2 = build_request("POST", url, body="username=student&password=training123")
        resp1, resp2 = app1.handle(req1), app2.handle(req2)
        assert resp1.cookies["session_id"] == resp2.cookies["session_id"] == "student-session"


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "web-fundamentals" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("web-fundamentals")
        assert m is not None
        assert m["title"] == "Web Fundamentals"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 450

    def test_objective_count(self):
        m = get_mission("web-fundamentals")
        assert len(m["objectives"]) == 12

    def test_xp_sums_to_total(self):
        m = get_mission("web-fundamentals")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_chained_after_wireshark_fundamentals(self):
        assert MISSIONS["wireshark-fundamentals"]["next_mission"] == "web-fundamentals"

    def test_web_lab_flag_set(self):
        m = get_mission("web-fundamentals")
        assert m["web_lab"] is True

    def test_web_workspace_seeded(self):
        m = get_mission("web-fundamentals")
        assert "web" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("web-fundamentals", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 450
        assert set(r.progress.completed_ids) == {f"wb-{i}" for i in range(1, 13)}

    def test_session_objective_not_gamed_by_login_alone(self):
        r = MissionRunner("web-fundamentals", 2)
        r.execute('open -X POST -d "username=student&password=training123" '
                 'https://cybershop.training/login')
        assert "wb-10" not in r.progress.completed_ids
        r.execute("open https://cybershop.training/profile")
        assert "wb-10" in r.progress.completed_ids

    def test_redirect_objective_not_gamed_by_visiting_destination(self):
        r = MissionRunner("web-fundamentals", 3)
        r.execute("open https://cybershop.training/auth/login")
        assert "wb-11" not in r.progress.completed_ids
        r.execute("open https://cybershop.training/login")
        assert "wb-11" in r.progress.completed_ids

    def test_final_investigation_requires_written_conclusion(self):
        r = MissionRunner("web-fundamentals", 4)
        r.execute("evidence")
        r.execute("inspect 1")
        r.execute("inspect 2")
        r.execute("inspect 3")
        assert "wb-12" not in r.progress.completed_ids
        r.execute('echo "no session cookie" > web/investigation.txt')
        assert "wb-12" in r.progress.completed_ids

    def test_progress_partial(self):
        r = MissionRunner("web-fundamentals", 5)
        r.execute("open https://cybershop.training/products?id=42")
        assert len(r.progress.completed_ids) >= 1
        assert not r.progress.completed

    def test_hint(self):
        r = MissionRunner("web-fundamentals", 6)
        hint = r.use_hint("wb-5")
        assert "does-not-exist" in hint
        assert r.progress.hints_used == 1

    def test_ai_context_includes_web_status(self):
        r = MissionRunner("web-fundamentals", 7)
        r.execute("open https://cybershop.training/")
        ctx = r.ai_context()
        assert ctx["web"]["last_status"] == 200
        assert ctx["web"]["last_path"] == "/"

    def test_save_restore_preserves_login_state(self):
        r = MissionRunner("web-fundamentals", 8)
        r.execute('open -X POST -d "username=student&password=training123" '
                 'https://cybershop.training/login')
        state = r.save_state()
        r2 = MissionRunner.from_state(state)
        status = r2.web_lab_status()
        assert status["logged_in_as"] == "student"
        out = r2.shell.execute("open https://cybershop.training/profile")
        assert "Profile: student" in out

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("web-fundamentals", 9)
        r1.execute('open -X POST -d "username=student&password=training123" '
                  'https://cybershop.training/login')
        r2 = MissionRunner("web-fundamentals", 10)
        assert r2.web_lab_status()["logged_in_as"] is None


# ═══════════════════════════════════════════
# Services — status/chain, persistence, real XP engine
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
        u = User(username="web_test", email="webtest@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "web_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


_PREREQ_MISSIONS: list[tuple[str, list[str]]] = [
    ("linux-basics", ["pwd", "ls", "ls -la", "cd Documents", "cat welcome.txt",
                      "cd ~", "touch notes.txt", "mkdir practice", "history"]),
    ("linux-permissions", ["cd permissions", "ls -l", "whoami", "id", "groups",
                           "cat private.txt", "chmod 644 challenge.txt",
                           "ls -l challenge.txt", "chown student private.txt"]),
    ("bash-fundamentals", ["cd bash-lab", 'name="student"', 'echo "$name"',
                           'export LAB="yushacyber"', 'echo "$LAB"', "current=$(pwd)",
                           "ls | grep txt", "ls > output.txt",
                           '''echo 'echo "Hello from YushaCyber!"' > script.sh''',
                           "chmod +x script.sh", "./script.sh",
                           'if [ -f script.sh ]; then echo "found"; fi',
                           'for i in 1 2 3; do echo "count-$i"; done']),
    ("networking-fundamentals", ["ip addr", "ip route", "ping 10.10.10.1",
                                 "ping 10.10.10.10", "ss", "nslookup example.local",
                                 "cat /etc/hosts", "ping 10.10.10.30"]),
    ("network-troubleshooting", ["ping 10.10.10.1", "ip link", "ip link set eth0 up",
                                 "ip addr", "ip addr add 10.10.10.20/24 dev eth0",
                                 "ip route", "ip route add default via 10.10.10.1",
                                 "ping 10.10.10.1", "ping 10.10.10.10",
                                 "nslookup example.local", "ss"]),
    ("nmap-fundamentals", ["nmap 10.10.10.10", "nmap -p 22,80,443 10.10.10.10",
                           "nmap -sV 10.10.10.10", "nmap -sT 10.10.10.10",
                           "nmap -sU 10.10.10.53", "nmap 10.10.10.40",
                           "nmap -Pn -O 10.10.10.40", "nmap -sV 10.10.10.30"]),
    ("network-reconnaissance", [
        "nmap -sn 10.10.10.0/24", "nmap 10.10.10.40", "nmap -p- 10.10.10.40",
        "nmap -sV 10.10.10.40", "nmap -sV 10.10.10.30",
        ('echo "Host: 10.10.10.40 (training-server) - Ports: 22,3306,8080 - Services: '
         'SSH,MySQL,HTTP" > recon/findings.txt'),
        'echo "TARGET: 10.10.10.40" >> recon/findings.txt',
        'echo "Services: SSH,MySQL,HTTP" >> recon/findings.txt',
        ('echo "PRIMARY TARGET CONFIRMED: 10.10.10.40 exposes SSH, MySQL, and HTTP - '
         'highest service diversity" >> recon/findings.txt'),
    ]),
    ("wireshark-fundamentals", [
        "capture handshake", "show 1", "filter tcp", "follow 1",
        "capture mixed", "filter dns",
        "capture http", "filter http", "follow 1",
        "filter ip.addr == 10.10.10.10", "filter tcp.port == 80",
        "capture mixed", "packets",
        "capture investigation", "filter ip.addr == 10.10.10.77",
        ('echo "Source: 10.10.10.20, Destination: 10.10.10.77, Port: 4444, Protocol: TCP, '
         'Reason: uncommon destination and port not part of normal training traffic" '
         '> wireshark/investigation.txt'),
    ]),
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

            assert mission_status(uid, "web-fundamentals") == "locked"

            for slug, commands in _PREREQ_MISSIONS:
                start_mission(uid, slug)
                for c in commands:
                    execute_command(uid, slug, c)

            assert mission_status(uid, "web-fundamentals") == "available"

            start_mission(uid, "web-fundamentals")
            for c in SOLVE:
                execute_command(uid, "web-fundamentals", c)

            assert mission_status(uid, "web-fundamentals") == "completed"

            user = User.query.get(uid)
            # 200+200+250+300+350+400+450+450+450 = 3050 base, plus bonuses.
            assert user.xp > 3050
            assert user.level > 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] == 9
            assert stats["xp_earned"] > 3050


# ═══════════════════════════════════════════
# HTTP — discovery/detail/terminal pick up the new mission automatically
# ═══════════════════════════════════════════
class TestHTTP:
    def test_discover_page_lists_web_fundamentals(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
            assert b"Web Fundamentals" in r.data

    def test_detail_page(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs/web-fundamentals")
            assert r.status_code == 200
            assert b"Query parameters" in r.data

    def test_terminal_page_shows_web_session_panel(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/web-fundamentals")
            assert r.status_code == 200
            assert b"data-web-status" in r.data

    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "web-fundamentals" in ids
