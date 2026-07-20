"""Web Security Scenario Engine (YC-029.0).

Simulates a vulnerable web application entirely in Python — no real
HTTP server, no real database, no real XSS execution. Each scenario
defines endpoints, parameters, expected exploits, and correct
mitigations. The engine evaluates student inputs against predefined
patterns and returns simulated HTTP responses.

Architecture:
  · Scenario    — one vulnerable web app (endpoints, params, vulns)
  · Endpoint    — one URL path with method, params, response template
  · WebApp      — runtime state (cookies, session, request history)
  · Evaluator   — checks if a student's input matches the exploit/fix
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import hashlib
import json
import re


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class HttpRequest:
    """A simulated HTTP request."""
    method: str = "GET"
    path: str = "/"
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method, "path": self.path,
            "headers": dict(self.headers), "cookies": dict(self.cookies),
            "params": dict(self.params), "body": self.body,
        }


@dataclass
class HttpResponse:
    """A simulated HTTP response."""
    status_code: int = 200
    status_text: str = "OK"
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    body: str = ""
    vulnerable: bool = False
    vulnerability_type: str = ""
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code, "status_text": self.status_text,
            "headers": dict(self.headers), "cookies": dict(self.cookies),
            "body": self.body[:2000],
        }


@dataclass
class Endpoint:
    """One URL path in the simulated web app."""
    path: str
    method: str = "GET"
    params: list[str] = field(default_factory=list)
    description: str = ""
    response_template: str = ""
    vulnerable_param: str = ""
    vulnerability_type: str = ""    # sqli, xss, csrf, auth_bypass, etc.
    exploit_pattern: str = ""       # regex the student's input must match
    mitigation: str = ""            # correct fix description
    requires_auth: bool = False
    response_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Scenario:
    """One vulnerable web application scenario."""
    id: str
    title: str
    description: str
    base_url: str = "http://vulnerable-app.local"
    endpoints: list[Endpoint] = field(default_factory=list)
    default_headers: dict[str, str] = field(default_factory=dict)
    default_cookies: dict[str, str] = field(default_factory=dict)
    session_config: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# WebApp runtime — manages cookies, sessions, request history
# ---------------------------------------------------------------------------
class WebApp:
    """Runtime state for one scenario. Tracks cookies, sessions,
    request history, and authentication state."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.cookies: dict[str, str] = dict(scenario.default_cookies)
        self.session: dict[str, Any] = {}
        self.authenticated: bool = False
        self.history: list[dict[str, Any]] = []
        self._endpoints: dict[str, Endpoint] = {
            f"{e.method}:{e.path}": e for e in scenario.endpoints
        }

    def handle_request(self, req: HttpRequest) -> HttpResponse:
        """Process a simulated HTTP request and return a response."""
        # Record in history
        self.history.append(req.to_dict())

        # Merge cookies
        self.cookies.update(req.cookies)

        # Find matching endpoint
        key = f"{req.method.upper()}:{req.path}"
        endpoint = self._endpoints.get(key)
        if endpoint is None:
            # Try wildcard GET
            endpoint = self._endpoints.get(f"GET:{req.path}")
        if endpoint is None:
            return HttpResponse(
                status_code=404, status_text="Not Found",
                body=f"<h1>404 Not Found</h1><p>{req.path} does not exist.</p>",
                headers={"Content-Type": "text/html"},
            )

        # Auth check
        if endpoint.requires_auth and not self.authenticated:
            return HttpResponse(
                status_code=401, status_text="Unauthorized",
                body="<h1>401 Unauthorized</h1><p>Login required.</p>",
                headers={"Content-Type": "text/html"},
            )

        # Build response
        response = self._build_response(endpoint, req)
        return response

    def _build_response(self, endpoint: Endpoint, req: HttpRequest) -> HttpResponse:
        """Generate the response, injecting vulnerability indicators."""
        # Default response headers
        headers = {
            "Content-Type": "text/html",
            "Server": "VulnApp/1.0",
            **self.scenario.default_headers,
            **endpoint.response_headers,
        }

        # Process parameters for vulnerability detection
        vuln_triggered = False
        vuln_detail = ""
        body = endpoint.response_template or f"<h1>{endpoint.description}</h1>"

        # Check if any param matches the exploit pattern
        all_params = {**req.params}
        if req.body:
            # Parse form-encoded body
            for pair in req.body.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    all_params[k] = v

        for param_name, param_value in all_params.items():
            if param_name == endpoint.vulnerable_param and endpoint.exploit_pattern:
                if re.search(endpoint.exploit_pattern, param_value, re.IGNORECASE):
                    vuln_triggered = True
                    vuln_detail = self._vuln_response(
                        endpoint.vulnerability_type, param_name, param_value, endpoint)

        if vuln_triggered:
            body = vuln_detail
        else:
            # Substitute params into template
            for k, v in all_params.items():
                body = body.replace(f"{{{k}}}", _safe_display(v))

        # Handle login endpoint
        if endpoint.path == "/login" and req.method.upper() == "POST":
            user = all_params.get("username", "")
            pwd = all_params.get("password", "")
            if self._check_login(user, pwd, endpoint):
                self.authenticated = True
                session_id = hashlib.md5(f"{user}:{pwd}".encode()).hexdigest()[:16]
                self.cookies["session_id"] = session_id
                self.session["user"] = user
                headers["Set-Cookie"] = f"session_id={session_id}; Path=/"
                body = f"<h1>Welcome, {_safe_display(user)}</h1><p>Login successful.</p>"

        return HttpResponse(
            status_code=200, status_text="OK",
            headers=headers, cookies=dict(self.cookies),
            body=body, vulnerable=vuln_triggered,
            vulnerability_type=endpoint.vulnerability_type if vuln_triggered else "",
        )

    def _check_login(self, user: str, pwd: str, endpoint: Endpoint) -> bool:
        """Check credentials. If the endpoint is vulnerable to SQLi,
        the classic ' OR 1=1-- pattern bypasses auth."""
        if endpoint.vulnerability_type == "sqli":
            if re.search(r"['\"]\s*(OR|or)\s+\d+=\d+", user) or \
               re.search(r"['\"]\s*(OR|or)\s+\d+=\d+", pwd):
                return True
        return user == "admin" and pwd == "password123"

    def _vuln_response(self, vuln_type: str, param: str, value: str,
                       endpoint: Endpoint) -> str:
        """Generate a response showing the vulnerability was triggered."""
        if vuln_type == "sqli":
            return (
                f"<h1>SQL Error</h1>"
                f"<p>You have an error in your SQL syntax near '{_safe_display(value)}'</p>"
                f"<pre>SELECT * FROM users WHERE {param} = '{_safe_display(value)}'</pre>"
                f"<p class='vuln-found'>⚠️ SQL Injection detected in parameter '{param}'!</p>"
                f"<p class='mitigation'>Mitigation: {endpoint.mitigation}</p>"
            )
        if vuln_type == "xss":
            return (
                f"<h1>Search Results</h1>"
                f"<p>Results for: {_safe_display(value)}</p>"
                f"<p class='vuln-found'>⚠️ Reflected XSS detected! The input was rendered unsanitised.</p>"
                f"<p>In a real app, the script tag would execute in the victim's browser.</p>"
                f"<p class='mitigation'>Mitigation: {endpoint.mitigation}</p>"
            )
        if vuln_type == "csrf":
            return (
                f"<h1>Action Completed</h1>"
                f"<p>Transfer of $1000 processed.</p>"
                f"<p class='vuln-found'>⚠️ CSRF vulnerability! No token validation was performed.</p>"
                f"<p class='mitigation'>Mitigation: {endpoint.mitigation}</p>"
            )
        if vuln_type == "auth_bypass":
            return (
                f"<h1>Admin Panel</h1>"
                f"<p>Welcome to the admin dashboard.</p>"
                f"<p class='vuln-found'>⚠️ Authorization bypass! No role check was performed.</p>"
                f"<p class='mitigation'>Mitigation: {endpoint.mitigation}</p>"
            )
        if vuln_type == "file_upload":
            return (
                f"<h1>Upload Complete</h1>"
                f"<p>File '{_safe_display(value)}' uploaded successfully.</p>"
                f"<p class='vuln-found'>⚠️ Dangerous file type accepted without validation!</p>"
                f"<p class='mitigation'>Mitigation: {endpoint.mitigation}</p>"
            )
        return f"<p class='vuln-found'>⚠️ Vulnerability triggered in '{param}'!</p>"


def _safe_display(value: str) -> str:
    """Escape HTML for display — we show what the input WAS, but never
    actually execute it."""
    return (value.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# Predefined scenarios
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, Scenario] = {}


def _register_scenarios():
    """Build the scenario catalogue. Called once at import time."""

    # --- Scenario 1: HTTP Basics ---
    SCENARIOS["http-basics"] = Scenario(
        id="http-basics",
        title="HTTP Request Explorer",
        description="Learn how HTTP requests and responses work.",
        base_url="http://example-app.local",
        endpoints=[
            Endpoint(
                path="/", method="GET", description="Home Page",
                response_template="<h1>Welcome to Example App</h1><p>Try different endpoints.</p>",
                response_headers={"X-Powered-By": "Express", "X-Frame-Options": "DENY"},
            ),
            Endpoint(
                path="/api/users", method="GET", description="User List API",
                params=["page", "limit"],
                response_template='{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "page": {page}}',
                response_headers={"Content-Type": "application/json"},
            ),
            Endpoint(
                path="/api/users", method="POST", description="Create User",
                params=["username", "email"],
                response_template='{"created": true, "username": "{username}"}',
                response_headers={"Content-Type": "application/json"},
            ),
            Endpoint(
                path="/headers", method="GET", description="Header Inspector",
                response_template="<h1>Request Headers</h1><p>Your User-Agent and cookies are logged.</p>",
            ),
        ],
        default_headers={"X-Content-Type-Options": "nosniff"},
    )

    # --- Scenario 2: SQL Injection ---
    SCENARIOS["sqli-login"] = Scenario(
        id="sqli-login",
        title="SQL Injection — Login Bypass",
        description="A login form vulnerable to SQL injection.",
        base_url="http://vuln-login.local",
        endpoints=[
            Endpoint(
                path="/", method="GET", description="Login Page",
                response_template=(
                    "<h1>Login</h1>"
                    "<form method='POST' action='/login'>"
                    "<input name='username' placeholder='Username'>"
                    "<input name='password' type='password' placeholder='Password'>"
                    "<button type='submit'>Login</button></form>"
                ),
            ),
            Endpoint(
                path="/login", method="POST", description="Login Handler",
                params=["username", "password"],
                vulnerable_param="username",
                vulnerability_type="sqli",
                exploit_pattern=r"['\"].*(?:OR|or)\s+\d+=\d+",
                mitigation="Use parameterized queries (prepared statements). Never concatenate user input into SQL strings.",
                response_template="<h1>Login Failed</h1><p>Invalid credentials.</p>",
            ),
            Endpoint(
                path="/dashboard", method="GET", description="Dashboard (auth required)",
                requires_auth=True,
                response_template="<h1>Dashboard</h1><p>Welcome, authenticated user.</p>",
            ),
        ],
    )

    # --- Scenario 3: XSS ---
    SCENARIOS["xss-reflected"] = Scenario(
        id="xss-reflected",
        title="Cross-Site Scripting — Reflected",
        description="A search page that reflects user input without sanitisation.",
        base_url="http://vuln-search.local",
        endpoints=[
            Endpoint(
                path="/", method="GET", description="Home Page",
                response_template="<h1>Search Engine</h1><form action='/search'><input name='q'><button>Search</button></form>",
            ),
            Endpoint(
                path="/search", method="GET", description="Search Results",
                params=["q"],
                vulnerable_param="q",
                vulnerability_type="xss",
                exploit_pattern=r"<script|javascript:|onerror|onload|<img",
                mitigation="Escape all user output using HTML entity encoding. Use Content-Security-Policy headers.",
                response_template="<h1>Search Results</h1><p>You searched for: {q}</p><p>No results found.</p>",
            ),
        ],
    )

    # --- Scenario 4: CSRF ---
    SCENARIOS["csrf-transfer"] = Scenario(
        id="csrf-transfer",
        title="Cross-Site Request Forgery",
        description="A bank transfer form without CSRF token validation.",
        base_url="http://vuln-bank.local",
        endpoints=[
            Endpoint(
                path="/", method="GET", description="Account Overview",
                response_template="<h1>Your Account</h1><p>Balance: $5,000</p><a href='/transfer'>Transfer Money</a>",
            ),
            Endpoint(
                path="/transfer", method="GET", description="Transfer Form",
                response_template=(
                    "<h1>Transfer Money</h1>"
                    "<form method='POST' action='/transfer'>"
                    "<input name='to' placeholder='Recipient'>"
                    "<input name='amount' placeholder='Amount'>"
                    "<button>Transfer</button></form>"
                    "<p>⚠️ Notice: No CSRF token in this form!</p>"
                ),
            ),
            Endpoint(
                path="/transfer", method="POST", description="Process Transfer",
                params=["to", "amount"],
                vulnerable_param="amount",
                vulnerability_type="csrf",
                exploit_pattern=r".+",  # any amount triggers — the vuln IS the missing token
                mitigation="Include a unique CSRF token in every state-changing form. Validate it server-side.",
            ),
        ],
        default_cookies={"session_id": "abc123def456"},
    )

    # --- Scenario 5: Cookies & Sessions ---
    SCENARIOS["session-security"] = Scenario(
        id="session-security",
        title="Cookie & Session Security",
        description="Inspect session cookies and their security flags.",
        base_url="http://session-demo.local",
        endpoints=[
            Endpoint(
                path="/", method="GET", description="Home Page",
                response_template="<h1>Session Demo</h1><p>Login to get a session cookie.</p>",
                response_headers={
                    "Set-Cookie": "session_id=insecure123; Path=/",
                },
            ),
            Endpoint(
                path="/login", method="POST", description="Login",
                params=["username", "password"],
                response_template="<h1>Logged In</h1><p>Check your cookies.</p>",
                response_headers={
                    "Set-Cookie": "session_id=insecure123; Path=/",
                },
            ),
            Endpoint(
                path="/secure-login", method="POST", description="Secure Login",
                params=["username", "password"],
                response_template="<h1>Securely Logged In</h1><p>Notice the cookie flags.</p>",
                response_headers={
                    "Set-Cookie": "session_id=secure456; Path=/; Secure; HttpOnly; SameSite=Strict",
                },
            ),
        ],
        default_cookies={"session_id": "insecure123"},
        session_config={"secure": False, "httponly": False, "samesite": "None"},
    )

    # --- Scenario 6: Security Headers ---
    SCENARIOS["security-headers"] = Scenario(
        id="security-headers",
        title="Security Headers Analysis",
        description="Analyse which security headers are present or missing.",
        base_url="http://headers-demo.local",
        endpoints=[
            Endpoint(
                path="/insecure", method="GET", description="Insecure Page",
                response_template="<h1>Insecure Page</h1><p>This page is missing important security headers.</p>",
                response_headers={"Server": "Apache/2.4.1"},
            ),
            Endpoint(
                path="/secure", method="GET", description="Secure Page",
                response_template="<h1>Secure Page</h1><p>This page has proper security headers.</p>",
                response_headers={
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Content-Security-Policy": "default-src 'self'",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                    "Permissions-Policy": "camera=(), microphone=()",
                },
            ),
        ],
    )

    # --- Scenario 7: File Upload ---
    SCENARIOS["file-upload"] = Scenario(
        id="file-upload",
        title="File Upload Validation",
        description="A file upload form that doesn't validate file types.",
        base_url="http://upload-demo.local",
        endpoints=[
            Endpoint(
                path="/", method="GET", description="Upload Page",
                response_template=(
                    "<h1>Upload a Profile Picture</h1>"
                    "<form method='POST' action='/upload'>"
                    "<input name='filename' placeholder='filename.jpg'>"
                    "<button>Upload</button></form>"
                ),
            ),
            Endpoint(
                path="/upload", method="POST", description="Upload Handler",
                params=["filename"],
                vulnerable_param="filename",
                vulnerability_type="file_upload",
                exploit_pattern=r"\.(php|jsp|asp|exe|sh|py|pl|cgi)$",
                mitigation="Validate file extensions against a whitelist. Check MIME types. Store uploads outside the web root.",
                response_template="<h1>Upload Complete</h1><p>File '{filename}' uploaded.</p>",
            ),
        ],
    )

    # --- Scenario 8: Authorization ---
    SCENARIOS["auth-bypass"] = Scenario(
        id="auth-bypass",
        title="Authorization Bypass — IDOR",
        description="An API endpoint that doesn't check user permissions.",
        base_url="http://vuln-api.local",
        endpoints=[
            Endpoint(
                path="/api/profile", method="GET", description="Your Profile",
                params=["user_id"],
                response_template='{"user_id": {user_id}, "name": "Current User", "email": "user@example.com"}',
                response_headers={"Content-Type": "application/json"},
            ),
            Endpoint(
                path="/api/admin", method="GET", description="Admin Panel",
                params=["role"],
                vulnerable_param="role",
                vulnerability_type="auth_bypass",
                exploit_pattern=r"admin",
                mitigation="Check authorization server-side. Never rely on client-supplied role parameters.",
                response_template='{"error": "Access denied"}',
                response_headers={"Content-Type": "application/json"},
            ),
        ],
    )


_register_scenarios()


# ---------------------------------------------------------------------------
# Scenario loader (for lab seed + runtime)
# ---------------------------------------------------------------------------
def get_scenario(scenario_id: str) -> Optional[Scenario]:
    return SCENARIOS.get(scenario_id)

def list_scenarios() -> list[str]:
    return sorted(SCENARIOS.keys())
