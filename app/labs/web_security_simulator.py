"""Interactive Web Security Lab Simulator (YC-029.0).

A scenario-driven simulator where each lab presents simulated HTTP
exchanges with deliberate vulnerabilities. Students use terminal
commands to inspect requests/responses, modify parameters, and
identify security flaws — all sandboxed inside the browser.

Architecture:
  · Scenario Engine — each scenario is a data dict with a request,
    response, vulnerability type, and acceptance criteria
  · HTTP Explorer — ``http``, ``headers``, ``cookies``, ``params``
    commands to inspect the current exchange
  · Request Modifier — ``set header/cookie/param/method/body``
    commands to alter the request and re-submit
  · Vulnerability Testers — ``sqli test``, ``xss test``, ``csrf check``
    evaluate student inputs against predefined patterns
  · ``answer`` command — submit the identified vulnerability or
    mitigation for objective validation

Nothing executes real HTTP, SQL, or JavaScript. Every response is
precomputed from the scenario data.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_TERMINAL,
    Action,
    ActionResult,
    Simulator,
)


# ---------------------------------------------------------------------------
# Scenario definitions — the 10 modules from the ticket
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, dict[str, Any]] = {
    "http-basics": {
        "title": "HTTP Requests & Responses",
        "description": "Inspect a basic HTTP GET request and understand the response.",
        "request": {
            "method": "GET", "url": "/dashboard", "http_version": "HTTP/1.1",
            "headers": {
                "Host": "vulnerable-app.local",
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Cookie": "session=abc123def456",
            },
            "params": {"user": "admin"},
            "body": "",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {
                "Content-Type": "text/html; charset=utf-8",
                "Server": "Apache/2.4.58",
                "Set-Cookie": "session=abc123def456; Path=/",
                "X-Powered-By": "PHP/8.2",
            },
            "body": "<html><body><h1>Welcome admin</h1></body></html>",
        },
        "vulnerability": None,
        "module": "http",
    },
    "cookie-flags": {
        "title": "Cookie Security Flags",
        "description": "Identify missing security flags on session cookies.",
        "request": {
            "method": "GET", "url": "/account", "http_version": "HTTP/1.1",
            "headers": {
                "Host": "shop.example.com",
                "Cookie": "sessionid=a1b2c3d4e5; preferences=dark",
            },
            "params": {},
            "body": "",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {
                "Set-Cookie": "sessionid=a1b2c3d4e5; Path=/",
                "Content-Type": "text/html",
            },
            "body": "<html><body>Account page</body></html>",
        },
        "vulnerability": "missing-cookie-flags",
        "answer_keywords": ["secure", "httponly", "samesite"],
        "explanation": "The session cookie lacks Secure, HttpOnly, and SameSite flags. Without Secure, it transmits over HTTP. Without HttpOnly, JavaScript can steal it. Without SameSite, CSRF attacks can ride it.",
        "module": "cookies",
    },
    "session-fixation": {
        "title": "Session Management",
        "description": "The server reuses the session ID after login — a session fixation risk.",
        "request": {
            "method": "POST", "url": "/login", "http_version": "HTTP/1.1",
            "headers": {
                "Host": "app.example.com",
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": "sessionid=ATTACKER_KNOWN_ID",
            },
            "params": {},
            "body": "username=admin&password=secret123",
        },
        "response": {
            "status": 302, "status_text": "Found",
            "headers": {
                "Location": "/dashboard",
                "Set-Cookie": "sessionid=ATTACKER_KNOWN_ID; Path=/",
            },
            "body": "",
        },
        "vulnerability": "session-fixation",
        "answer_keywords": ["fixation", "regenerate", "new session"],
        "explanation": "The server kept the same session ID (ATTACKER_KNOWN_ID) after login instead of regenerating it. An attacker who sets this ID beforehand can hijack the authenticated session.",
        "module": "sessions",
    },
    "auth-bypass": {
        "title": "Authentication Bypass",
        "description": "A login form sends credentials in the URL. Inspect the request.",
        "request": {
            "method": "GET", "url": "/login?username=admin&password=P%40ssw0rd", "http_version": "HTTP/1.1",
            "headers": {
                "Host": "internal.example.com",
            },
            "params": {"username": "admin", "password": "P@ssw0rd"},
            "body": "",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {"Content-Type": "text/html"},
            "body": "<html><body>Login form</body></html>",
        },
        "vulnerability": "credentials-in-url",
        "answer_keywords": ["get", "url", "password", "query string", "post"],
        "explanation": "Credentials are sent via GET in the query string, which gets logged in browser history, server logs, and referrer headers. The login form should use POST over HTTPS.",
        "module": "authentication",
    },
    "idor": {
        "title": "Authorization — IDOR",
        "description": "The API exposes user data by sequential ID with no access control.",
        "request": {
            "method": "GET", "url": "/api/users/1042", "http_version": "HTTP/1.1",
            "headers": {
                "Host": "api.example.com",
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.user1041",
                "Accept": "application/json",
            },
            "params": {},
            "body": "",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {"Content-Type": "application/json"},
            "body": '{"id": 1042, "name": "Alice Smith", "email": "alice@example.com", "ssn": "123-45-6789"}',
        },
        "vulnerability": "idor",
        "answer_keywords": ["idor", "insecure direct object", "authorization", "access control"],
        "explanation": "User 1041's token can access user 1042's data by changing the ID in the URL. The server doesn't verify that the authenticated user owns the requested resource.",
        "module": "authorization",
    },
    "sqli-login": {
        "title": "SQL Injection — Login Bypass",
        "description": "A login form is vulnerable to SQL injection. Identify the vulnerable parameter.",
        "request": {
            "method": "POST", "url": "/login", "http_version": "HTTP/1.1",
            "headers": {
                "Host": "vulnerable-app.local",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            "params": {},
            "body": "username=admin&password=password123",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {"Content-Type": "text/html"},
            "body": "<html><body><p>Invalid credentials</p></body></html>",
        },
        "vulnerability": "sql-injection",
        "sqli_field": "username",
        "sqli_payloads": ["' OR 1=1--", "' OR '1'='1", "admin'--", "' UNION SELECT"],
        "sqli_success_response": '<html><body><h1>Welcome admin</h1><p>Dashboard loaded.</p></body></html>',
        "answer_keywords": ["sql injection", "sqli", "username", "parameterized", "prepared statement"],
        "explanation": "The username field is concatenated directly into SQL. The payload ' OR 1=1-- bypasses authentication because the query becomes: SELECT * FROM users WHERE username='' OR 1=1--' AND password='...'",
        "module": "sqli",
    },
    "xss-reflected": {
        "title": "Cross-Site Scripting — Reflected",
        "description": "A search page reflects user input without sanitization.",
        "request": {
            "method": "GET", "url": "/search?q=laptop", "http_version": "HTTP/1.1",
            "headers": {"Host": "shop.example.com"},
            "params": {"q": "laptop"},
            "body": "",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {"Content-Type": "text/html"},
            "body": '<html><body><h2>Search results for: laptop</h2><p>No results found.</p></body></html>',
        },
        "vulnerability": "xss-reflected",
        "xss_field": "q",
        "xss_payloads": ["<script>alert(1)</script>", "<img onerror=alert(1) src=x>", "'\"><script>"],
        "xss_rendered": '<html><body><h2>Search results for: <script>alert(1)</script></h2><p>No results found.</p></body></html>',
        "answer_keywords": ["xss", "cross-site scripting", "reflected", "sanitize", "escape", "encode"],
        "explanation": "The search query parameter 'q' is reflected directly into the HTML without escaping. An attacker can inject <script> tags that execute in the victim's browser.",
        "module": "xss",
    },
    "csrf-transfer": {
        "title": "Cross-Site Request Forgery",
        "description": "A money transfer endpoint has no CSRF protection.",
        "request": {
            "method": "POST", "url": "/transfer", "http_version": "HTTP/1.1",
            "headers": {
                "Host": "bank.example.com",
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": "session=valid_user_session",
            },
            "params": {},
            "body": "to=attacker&amount=1000",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {"Content-Type": "text/html"},
            "body": "<html><body><p>Transfer of $1000 to attacker completed.</p></body></html>",
        },
        "vulnerability": "csrf",
        "answer_keywords": ["csrf", "cross-site request forgery", "token", "samesite"],
        "explanation": "The transfer endpoint accepts the request with only a session cookie — no CSRF token, no SameSite cookie flag, no Origin check. An attacker's page can submit this form on behalf of the authenticated user.",
        "module": "csrf",
    },
    "file-upload": {
        "title": "File Upload Validation",
        "description": "A file upload endpoint only checks the Content-Type header.",
        "request": {
            "method": "POST", "url": "/upload", "http_version": "HTTP/1.1",
            "headers": {
                "Host": "app.example.com",
                "Content-Type": "multipart/form-data",
            },
            "params": {},
            "body": "filename=profile.php\nContent-Type: image/jpeg\n\n<?php system($_GET['cmd']); ?>",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {"Content-Type": "application/json"},
            "body": '{"status": "success", "path": "/uploads/profile.php"}',
        },
        "vulnerability": "unrestricted-upload",
        "answer_keywords": ["file extension", "magic bytes", "whitelist", "upload", "php"],
        "explanation": "The server only checks Content-Type (which the client controls) but doesn't validate the actual file extension or content. A .php file with a faked image/jpeg Content-Type gets uploaded and can execute arbitrary commands.",
        "module": "file-upload",
    },
    "security-headers": {
        "title": "Security Headers Audit",
        "description": "Audit the response headers for missing security protections.",
        "request": {
            "method": "GET", "url": "/", "http_version": "HTTP/1.1",
            "headers": {"Host": "legacy-app.example.com"},
            "params": {},
            "body": "",
        },
        "response": {
            "status": 200, "status_text": "OK",
            "headers": {
                "Content-Type": "text/html",
                "Server": "Apache/2.4.41",
                "X-Powered-By": "PHP/7.4",
            },
            "body": "<html><body>Legacy app</body></html>",
        },
        "vulnerability": "missing-security-headers",
        "answer_keywords": ["csp", "content-security-policy", "x-frame-options",
                           "hsts", "strict-transport-security", "x-content-type-options"],
        "explanation": "The response is missing critical security headers: Content-Security-Policy (prevents XSS), X-Frame-Options (prevents clickjacking), Strict-Transport-Security (forces HTTPS), X-Content-Type-Options (prevents MIME sniffing). It also leaks server version info via Server and X-Powered-By.",
        "module": "headers",
    },
}


# ---------------------------------------------------------------------------
# The Simulator
# ---------------------------------------------------------------------------
@register_simulator
class WebSecuritySimulator(Simulator):
    """Scenario-based web security lab simulator (YC-029.0).

    Each lab loads a scenario by key from the SCENARIOS dict. The student
    uses terminal commands to inspect the HTTP exchange, modify the
    request, test for vulnerabilities, and submit their answer.
    """

    key = "web-security"
    capabilities_set = (CAP_TERMINAL,)

    # Lab slug → scenario key mapping (each lab loads its own scenario).
    SLUG_TO_SCENARIO = {
        "websec-http": "http-basics",
        "websec-cookies": "cookie-flags",
        "websec-sessions": "session-fixation",
        "websec-auth": "auth-bypass",
        "websec-idor": "idor",
        "websec-sqli": "sqli-login",
        "websec-xss": "xss-reflected",
        "websec-csrf": "csrf-transfer",
        "websec-upload": "file-upload",
        "websec-headers": "security-headers",
    }

    def capabilities(self) -> set[str]:
        return set(self.capabilities_set)

    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        # Resolve scenario from the lab slug or from the content dict.
        scenario_key = (content or {}).get("scenario", "http-basics")
        if lab is not None and hasattr(lab, "slug"):
            scenario_key = self.SLUG_TO_SCENARIO.get(lab.slug, scenario_key)
        scenario = SCENARIOS.get(scenario_key, SCENARIOS["http-basics"])
        return {
            "sim": self.key,
            "scenario_key": scenario_key,
            "request": dict(scenario["request"]),
            "response": dict(scenario["response"]),
            "original_request": dict(scenario["request"]),
            "modified": False,
            "submitted_answers": [],
            "sqli_tested": False,
            "xss_tested": False,
            "csrf_checked": False,
            "commands_used": 0,
            "flags": {},
        }

    def prompt(self, state: dict[str, Any]) -> str:
        scenario = SCENARIOS.get(state.get("scenario_key", ""), {})
        host = state.get("request", {}).get("headers", {}).get("Host", "target")
        return f"websec@{host}> "

    def welcome(self, state: dict[str, Any]) -> str:
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        return (
            f"Web Security Lab: {sc.get('title', 'Unknown')}\n"
            f"{sc.get('description', '')}\n"
            f"\n"
            f"Commands: http, headers, cookies, params, body, status,\n"
            f"          set, submit, sqli, xss, csrf, answer, help"
        )

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        req = state.get("request", {})
        resp = state.get("response", {})
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        return [
            {"label": "Module", "value": sc.get("module", "—")},
            {"label": "Method", "value": req.get("method", "GET")},
            {"label": "URL", "value": req.get("url", "/")},
            {"label": "Status", "value": f"{resp.get('status', '?')} {resp.get('status_text', '')}"},
            {"label": "Modified", "value": "Yes" if state.get("modified") else "No"},
        ]

    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        state = dict(state) if state else self.bootstrap(None, {})
        if action.type == "command":
            return self._handle_command(state, action)
        return ActionResult(new_state=state)

    def _handle_command(self, state: dict, action: Action) -> ActionResult:
        raw = action.command.strip()
        if not raw:
            return ActionResult(new_state=state)

        state["commands_used"] = state.get("commands_used", 0) + 1
        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        dispatch: dict[str, Callable] = {
            "help": self._cmd_help,
            "http": self._cmd_http,
            "headers": self._cmd_headers,
            "cookies": self._cmd_cookies,
            "params": self._cmd_params,
            "body": self._cmd_body,
            "status": self._cmd_status,
            "set": self._cmd_set,
            "submit": self._cmd_submit,
            "sqli": self._cmd_sqli,
            "xss": self._cmd_xss,
            "csrf": self._cmd_csrf,
            "answer": self._cmd_answer,
            "explain": self._cmd_explain,
            "clear": self._cmd_clear,
            "reset": self._cmd_reset,
        }

        handler = dispatch.get(cmd)
        if handler is None:
            return ActionResult(
                output=f"Unknown command: {cmd}. Type 'help' for available commands.",
                new_state=state)
        return handler(state, arg)

    # -- Commands ------------------------------------------------------
    def _cmd_help(self, state, arg):
        return ActionResult(output=(
            "Web Security Lab Commands:\n"
            "  http              show the full HTTP request\n"
            "  headers [req|res] show request or response headers\n"
            "  cookies           show cookies from the request\n"
            "  params            show query/body parameters\n"
            "  body [req|res]    show request or response body\n"
            "  status            show response status code\n"
            "  set <what> <val>  modify request (header, cookie, param, method, body)\n"
            "  submit            re-send the modified request\n"
            "  sqli test <input> test a field for SQL injection\n"
            "  xss test <input>  test a field for XSS\n"
            "  csrf check        check for CSRF protections\n"
            "  answer <text>     submit your vulnerability assessment\n"
            "  explain           show the vulnerability explanation\n"
            "  reset             reset the request to original\n"
            "  clear             clear the terminal"
        ), new_state=state, events=[{"type": "help_shown"}])

    def _cmd_http(self, state, arg):
        req = state["request"]
        lines = [f"{req['method']} {req['url']} {req['http_version']}"]
        for k, v in req.get("headers", {}).items():
            lines.append(f"{k}: {v}")
        if req.get("body"):
            lines.append("")
            lines.append(req["body"])
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "http_inspected", "method": req["method"]}])

    def _cmd_headers(self, state, arg):
        which = arg.strip().lower() if arg else "both"
        lines = []
        if which in ("req", "request", "both"):
            lines.append("── Request Headers ──")
            for k, v in state["request"].get("headers", {}).items():
                lines.append(f"  {k}: {v}")
        if which in ("res", "response", "both"):
            lines.append("── Response Headers ──")
            for k, v in state["response"].get("headers", {}).items():
                lines.append(f"  {k}: {v}")
        state.setdefault("flags", {})["headers_inspected"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "headers_inspected", "which": which}])

    def _cmd_cookies(self, state, arg):
        cookies = {}
        cookie_str = state["request"].get("headers", {}).get("Cookie", "")
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                cookies[k.strip()] = v.strip()
        set_cookie = state["response"].get("headers", {}).get("Set-Cookie", "")
        lines = ["── Request Cookies ──"]
        for k, v in cookies.items():
            lines.append(f"  {k} = {v}")
        if set_cookie:
            lines.append("── Set-Cookie Response ──")
            lines.append(f"  {set_cookie}")
            flags_present = []
            for flag in ["Secure", "HttpOnly", "SameSite"]:
                if flag.lower() in set_cookie.lower():
                    flags_present.append(f"  ✓ {flag}")
                else:
                    flags_present.append(f"  ✗ {flag} — MISSING")
            lines.append("── Cookie Flags ──")
            lines.extend(flags_present)
        state.setdefault("flags", {})["cookies_inspected"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "cookies_inspected",
                                     "missing_flags": [f for f in ["Secure","HttpOnly","SameSite"]
                                                       if f.lower() not in set_cookie.lower()]}])

    def _cmd_params(self, state, arg):
        req = state["request"]
        params = req.get("params", {})
        body_params = {}
        if "x-www-form-urlencoded" in req.get("headers", {}).get("Content-Type", ""):
            for pair in req.get("body", "").split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    body_params[k] = v
        lines = ["── Query Parameters ──"]
        for k, v in params.items():
            lines.append(f"  {k} = {v}")
        if not params:
            lines.append("  (none)")
        if body_params:
            lines.append("── Body Parameters ──")
            for k, v in body_params.items():
                lines.append(f"  {k} = {v}")
        state.setdefault("flags", {})["params_inspected"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "params_inspected",
                                     "param_names": list(params.keys()) + list(body_params.keys())}])

    def _cmd_body(self, state, arg):
        which = arg.strip().lower() if arg else "res"
        if which in ("req", "request"):
            body = state["request"].get("body", "(empty)")
        else:
            body = state["response"].get("body", "(empty)")
        state.setdefault("flags", {})["body_inspected"] = True
        return ActionResult(output=body or "(empty body)", new_state=state,
                            events=[{"type": "body_inspected", "which": which}])

    def _cmd_status(self, state, arg):
        resp = state["response"]
        return ActionResult(
            output=f"HTTP {resp.get('status', '?')} {resp.get('status_text', '')}",
            new_state=state,
            events=[{"type": "status_inspected", "code": resp.get("status")}])

    def _cmd_set(self, state, arg):
        parts = arg.split(None, 1) if arg else []
        if len(parts) < 2:
            return ActionResult(
                output="Usage: set <header|cookie|param|method|body> <value>\n"
                       "  set header X-Custom: value\n"
                       "  set cookie name=value\n"
                       "  set param key=value\n"
                       "  set method POST\n"
                       "  set body key=value&key2=value2",
                new_state=state)
        what, value = parts[0].lower(), parts[1]
        state["modified"] = True
        if what == "header":
            if ":" in value:
                k, v = value.split(":", 1)
                state["request"]["headers"][k.strip()] = v.strip()
                return ActionResult(output=f"Header set: {k.strip()}: {v.strip()}",
                                    new_state=state,
                                    events=[{"type": "request_modified", "what": "header"}])
        elif what == "cookie":
            existing = state["request"]["headers"].get("Cookie", "")
            state["request"]["headers"]["Cookie"] = f"{existing}; {value}" if existing else value
            return ActionResult(output=f"Cookie added: {value}", new_state=state,
                                events=[{"type": "request_modified", "what": "cookie"}])
        elif what == "param":
            if "=" in value:
                k, v = value.split("=", 1)
                state["request"]["params"][k] = v
                return ActionResult(output=f"Parameter set: {k}={v}", new_state=state,
                                    events=[{"type": "request_modified", "what": "param"}])
        elif what == "method":
            state["request"]["method"] = value.upper()
            return ActionResult(output=f"Method changed to {value.upper()}", new_state=state,
                                events=[{"type": "request_modified", "what": "method"}])
        elif what == "body":
            state["request"]["body"] = value
            return ActionResult(output=f"Body set: {value[:80]}", new_state=state,
                                events=[{"type": "request_modified", "what": "body"}])
        return ActionResult(output=f"Unknown target: {what}", new_state=state)

    def _cmd_submit(self, state, arg):
        state.setdefault("flags", {})["request_submitted"] = True
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        # For SQLi scenarios: check if the modified body contains a payload
        if sc.get("sqli_field") and state.get("modified"):
            body = state["request"].get("body", "")
            for payload in sc.get("sqli_payloads", []):
                if payload.lower() in body.lower():
                    state["response"]["body"] = sc.get("sqli_success_response", "Login successful")
                    state["response"]["status"] = 200
                    return ActionResult(
                        output=f"HTTP {state['response']['status']} {state['response']['status_text']}\n\n"
                               f"{state['response']['body']}",
                        new_state=state,
                        events=[{"type": "request_submitted", "sqli_success": True}])
        return ActionResult(
            output=f"HTTP {state['response']['status']} {state['response']['status_text']}\n\n"
                   f"{state['response']['body']}",
            new_state=state,
            events=[{"type": "request_submitted", "modified": state.get("modified", False)}])

    def _cmd_sqli(self, state, arg):
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        parts = arg.split(None, 1) if arg else []
        if not parts or parts[0].lower() != "test":
            return ActionResult(
                output="Usage: sqli test <payload>\nExample: sqli test ' OR 1=1--",
                new_state=state)
        payload = parts[1] if len(parts) > 1 else ""
        state["sqli_tested"] = True
        state.setdefault("flags", {})["sqli_tested"] = True
        if sc.get("vulnerability") == "sql-injection":
            for known in sc.get("sqli_payloads", []):
                if known.lower() in payload.lower() or payload.lower() in known.lower():
                    # Inject into body and show the result
                    field = sc.get("sqli_field", "input")
                    output = (
                        f"Testing: {payload}\n"
                        f"Injecting into field: {field}\n"
                        f"\n"
                        f"⚠ SQL Injection detected!\n"
                        f"The application returned the admin dashboard.\n"
                        f"The query became: SELECT * FROM users WHERE {field}='{payload}'\n"
                        f"\n"
                        f"Response:\n{sc.get('sqli_success_response', '')[:200]}"
                    )
                    return ActionResult(output=output, new_state=state,
                                        events=[{"type": "sqli_tested", "success": True,
                                                 "payload": payload}])
            return ActionResult(
                output=f"Testing: {payload}\nNo injection detected with this payload. Try a different approach.",
                new_state=state,
                events=[{"type": "sqli_tested", "success": False}])
        return ActionResult(
            output=f"Testing: {payload}\nThis scenario is not vulnerable to SQL injection.",
            new_state=state,
            events=[{"type": "sqli_tested", "success": False}])

    def _cmd_xss(self, state, arg):
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        parts = arg.split(None, 1) if arg else []
        if not parts or parts[0].lower() != "test":
            return ActionResult(output="Usage: xss test <payload>\nExample: xss test <script>alert(1)</script>",
                                new_state=state)
        payload = parts[1] if len(parts) > 1 else ""
        state["xss_tested"] = True
        state.setdefault("flags", {})["xss_tested"] = True
        if sc.get("vulnerability") == "xss-reflected":
            for known in sc.get("xss_payloads", []):
                if known.lower() in payload.lower() or "script" in payload.lower() or "onerror" in payload.lower():
                    field = sc.get("xss_field", "input")
                    output = (
                        f"Testing: {payload}\n"
                        f"Injecting into field: {field}\n"
                        f"\n"
                        f"⚠ Reflected XSS detected!\n"
                        f"The payload was reflected directly in the HTML without encoding.\n"
                        f"\n"
                        f"Rendered response:\n{sc.get('xss_rendered', '')[:200]}"
                    )
                    return ActionResult(output=output, new_state=state,
                                        events=[{"type": "xss_tested", "success": True,
                                                 "payload": payload}])
            return ActionResult(
                output=f"Testing: {payload}\nPayload was sanitized or not reflected.",
                new_state=state,
                events=[{"type": "xss_tested", "success": False}])
        return ActionResult(
            output=f"Testing: {payload}\nThis scenario is not vulnerable to XSS.",
            new_state=state,
            events=[{"type": "xss_tested", "success": False}])

    def _cmd_csrf(self, state, arg):
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        state["csrf_checked"] = True
        state.setdefault("flags", {})["csrf_checked"] = True
        req_headers = state["request"].get("headers", {})
        resp_headers = state["response"].get("headers", {})
        body = state["request"].get("body", "")
        checks = []
        has_token = "csrf" in body.lower() or "csrf" in str(req_headers).lower()
        checks.append(f"  {'✓' if has_token else '✗'} CSRF Token in request: {'Found' if has_token else 'MISSING'}")
        cookie = resp_headers.get("Set-Cookie", "")
        has_samesite = "samesite" in cookie.lower()
        checks.append(f"  {'✓' if has_samesite else '✗'} SameSite cookie flag: {'Set' if has_samesite else 'MISSING'}")
        has_origin = "Origin" in req_headers or "Referer" in req_headers
        checks.append(f"  {'✓' if has_origin else '✗'} Origin/Referer validation: {'Present' if has_origin else 'NOT CHECKED'}")
        vulnerable = not has_token and not has_samesite
        output = "── CSRF Protection Check ──\n" + "\n".join(checks)
        if vulnerable:
            output += "\n\n⚠ This endpoint appears vulnerable to CSRF attacks."
        else:
            output += "\n\n✓ CSRF protections appear adequate."
        return ActionResult(output=output, new_state=state,
                            events=[{"type": "csrf_checked", "vulnerable": vulnerable}])

    def _cmd_answer(self, state, arg):
        if not arg:
            return ActionResult(output="Usage: answer <your vulnerability assessment>",
                                new_state=state)
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        keywords = sc.get("answer_keywords", [])
        arg_lower = arg.lower()
        matched = [kw for kw in keywords if kw.lower() in arg_lower]
        is_correct = len(matched) >= 1 and keywords  # At least one keyword match
        state.setdefault("flags", {})["answer_submitted"] = True
        state["submitted_answers"].append(arg)
        if is_correct:
            state["flags"]["answer_correct"] = True
            output = (
                f"✓ Correct! You identified the vulnerability.\n"
                f"Matched concepts: {', '.join(matched)}\n"
                f"\n"
                f"Explanation:\n{sc.get('explanation', 'Good job!')}"
            )
        elif not keywords:
            state["flags"]["answer_correct"] = True
            output = "✓ This scenario has no specific vulnerability to identify. Good inspection work!"
        else:
            output = (
                f"✗ Not quite. Your answer didn't match the expected concepts.\n"
                f"Hint: Look more closely at the {sc.get('module', 'HTTP')} aspects of this exchange.\n"
                f"Try inspecting the headers, cookies, or parameters again."
            )
        return ActionResult(output=output, new_state=state,
                            events=[{"type": "answer_submitted", "correct": is_correct,
                                     "matched": matched}])

    def _cmd_explain(self, state, arg):
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        explanation = sc.get("explanation", "No specific vulnerability in this scenario.")
        state.setdefault("flags", {})["explanation_viewed"] = True
        return ActionResult(output=f"── Vulnerability Explanation ──\n{explanation}",
                            new_state=state,
                            events=[{"type": "explanation_viewed"}])

    def _cmd_clear(self, state, arg):
        return ActionResult(output="", new_state=state, clear=True)

    def _cmd_reset(self, state, arg):
        state["request"] = dict(state.get("original_request", state["request"]))
        state["modified"] = False
        return ActionResult(output="Request reset to original.", new_state=state,
                            events=[{"type": "request_reset"}])
