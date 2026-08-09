"""Simulated web application — YC-035.0 Web Fundamentals.

Independent from network.py (network state) and packets.py (packet
traffic) — this module simulates HTTP request/response exchanges against
one fictional training site ("CyberShop"). Like both of those, it is pure
in-memory data and string formatting: this module makes zero real network
requests, ever, to any host, real or otherwise. There is no outbound HTTP
client here at all (no `requests`, no `urllib.request`, no `http.client`,
no socket) — only `urllib.parse`, which is pure string parsing (splitting
a URL into pieces) and never opens a connection.

A request to any host other than the simulated one is rejected before it
would ever reach this module (see commands.py's `open`/`request`
handlers) — there is structurally nothing here that *could* make an
outbound call even if that check were bypassed.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlsplit

HOST = "cybershop.training"
SERVER_HEADER = "CyberShop-Sim/1.0"

# Training-only credentials — never real accounts.
_USERS = {"student": "training123", "analyst": "analyst123", "admin": "admin123"}

# Fixed training bearer token for the Authorization-header objective
# (YC-035.1) — a single, deterministic value, never a real secret.
API_TOKEN = "training-token-001"


@dataclass
class ParsedUrl:
    scheme: str
    host: str
    port: int
    path: str
    query: dict[str, str]
    fragment: str


def parse_url(url: str) -> ParsedUrl:
    """Split a URL into its components — pure string parsing, no I/O."""
    parts = urlsplit(url)
    scheme = parts.scheme or "https"
    host = parts.hostname or ""
    port = parts.port or (443 if scheme == "https" else 80)
    path = parts.path or "/"
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    return ParsedUrl(scheme=scheme, host=host, port=port, path=path,
                     query=query, fragment=parts.fragment or "")


def _parse_form(body: str) -> dict[str, str]:
    return dict(parse_qsl(body))


def parse_body(body: str, content_type: str) -> dict[str, Any]:
    """Parse a request/response body into a dict, per its Content-Type
    (YC-035.1) — pure parsing, mirrors _parse_form for JSON. Used by the
    'body_field' validator check so objectives can inspect a specific
    JSON/form field instead of substring-matching raw text."""
    if not body:
        return {}
    ct = (content_type or "").lower()
    if "json" in ct:
        try:
            data = json.loads(body)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}
    return _parse_form(body)


@dataclass
class HttpRequest:
    method: str
    scheme: str
    host: str
    port: int
    path: str
    query: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    body: str = ""
    timestamp: float = 0.0


@dataclass
class HttpResponse:
    status_code: int
    reason: str
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    # Cookie names the response tells the browser to delete (YC-035.3 —
    # logout). Kept separate from `cookies` (which only ever holds
    # *set* values) so render_response can emit the real
    # `Set-Cookie: name=; Max-Age=0` deletion form, and WebSession.record
    # can drop the name from its jar — the same distinction a real
    # browser makes between "set this cookie" and "delete this cookie".
    deleted_cookies: list[str] = field(default_factory=list)
    body: str = ""
    content_type: str = "text/plain"
    server: str = SERVER_HEADER


def build_request(method: str, url: ParsedUrl, body: str = "",
                  cookies: dict[str, str] | None = None,
                  timestamp: float = 0.0,
                  extra_headers: dict[str, str] | None = None) -> HttpRequest:
    headers = {
        "Host": url.host,
        "User-Agent": "YushaCyber-Trainer/1.0",
        "Accept": "*/*",
    }
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Content-Length"] = str(len(body))
    if extra_headers:
        # Applied after the defaults so a caller can override Content-Type
        # (e.g. to send JSON) or add Authorization/Referer (YC-035.1) —
        # the same curl-like '-H' mechanism a real HTTP client offers.
        headers.update(extra_headers)
        if body:
            headers["Content-Length"] = str(len(body))
    return HttpRequest(method=method.upper(), scheme=url.scheme, host=url.host,
                       port=url.port, path=url.path, query=dict(url.query),
                       headers=headers, cookies=dict(cookies or {}), body=body,
                       timestamp=timestamp)


class WebApp:
    """The simulated CyberShop training site. Routes are plain Python
    control flow over deterministic canned responses — never a real
    server, never a real socket."""

    def __init__(self, sessions: dict[str, str] | None = None,
                 profiles: dict[str, dict[str, Any]] | None = None) -> None:
        # session_id -> username. Mutated by successful logins/logouts,
        # exactly like VirtualNetwork's interface state (YC-034.6) —
        # small, explicit, session-scoped state.
        self.sessions: dict[str, str] = dict(sessions) if sessions else {}
        # username -> profile fields (YC-035.2) — mirrors self.sessions:
        # small, explicit, mutable, in-memory only. Lets POST /api/profile
        # have a real, observable effect instead of a no-op acknowledgment,
        # so proxy request-modification objectives have something genuine
        # to verify.
        self.profiles: dict[str, dict[str, Any]] = (
            dict(profiles) if profiles else {})

    def handle(self, req: HttpRequest) -> HttpResponse:
        if req.path == "/" and req.method == "GET":
            return self._ok("Welcome to CyberShop — a simulated training storefront.")
        if req.path == "/products" and req.method == "GET":
            return self._products(req)
        if req.path == "/search" and req.method == "GET":
            q = req.query.get("q", "")
            return self._ok(f"Search results for '{q}': 0 matches in the training catalog.")
        if req.path == "/login" and req.method == "GET":
            return self._redirect("/auth/login")
        if req.path == "/auth/login" and req.method == "GET":
            return self._ok("Please log in with your training account.")
        if req.path in ("/login", "/auth/login") and req.method == "POST":
            return self._login(req)
        if req.path == "/profile" and req.method == "GET":
            return self._profile(req)
        # POST /logout added alongside the existing GET /logout (YC-035.3)
        # — the actual training login/logout flow submits a form via POST;
        # GET stays for backward compatibility with earlier missions.
        if req.path == "/logout" and req.method in ("GET", "POST"):
            return self._logout(req)
        if req.path == "/account" and req.method == "GET":
            return self._account(req)
        if req.path == "/dashboard" and req.method == "GET":
            return self._dashboard(req)
        if req.path == "/admin" and req.method == "GET":
            return self._admin(req)
        if req.path == "/api/login" and req.method == "POST":
            return self._api_login(req)
        if req.path == "/api/profile" and req.method in ("GET", "POST"):
            return self._api_profile(req)
        if req.path == "/api/me" and req.method == "GET":
            return self._api_me(req)
        return self._not_found()

    def _products(self, req: HttpRequest) -> HttpResponse:
        pid = req.query.get("id")
        if pid:
            body = f"Product #{pid}: Sample training item."
            # Deterministic cache metadata (YC-035.1) — a fixed value, not a
            # real cache engine; "do NOT implement a complex cache engine...
            # a deterministic simulated response is enough".
            headers = {"Content-Type": "text/html", "Content-Length": str(len(body)),
                      "Server": SERVER_HEADER, "Cache-Control": "max-age=60",
                      "ETag": f'"product-{pid}-v1"',
                      "Last-Modified": "Wed, 01 Jan 2025 00:00:00 GMT"}
            return HttpResponse(status_code=200, reason="OK", body=body,
                                content_type="text/html", headers=headers)
        return self._ok("Product catalog: 3 items available.")

    def _check_credentials(self, req: HttpRequest) -> str | None:
        """Returns the matched training username, or None if invalid.
        Shared by the form-based and JSON login endpoints — same
        credentials, two different wire formats (YC-035.1)."""
        creds = parse_body(req.body, req.headers.get("Content-Type", ""))
        username, password = creds.get("username", ""), creds.get("password", "")
        if username in _USERS and _USERS[username] == password:
            return username
        return None

    def _login(self, req: HttpRequest) -> HttpResponse:
        username = self._check_credentials(req)
        if username:
            sid = f"{username}-session"
            self.sessions[sid] = username
            resp = self._redirect("/profile")
            resp.cookies["session_id"] = sid
            return resp
        # JSON failure body (YC-035.3) — same 401 status YC-035.0 already
        # locked in (test_login_post_invalid_credentials), just a
        # structured body instead of plain text, matching real login APIs
        # and the training spec's exact error shape. Never echoes back
        # the submitted password or any other secret.
        return self._json_error(401, "Unauthorized",
                                {"error": "Invalid training credentials"})

    def _profile(self, req: HttpRequest) -> HttpResponse:
        username = self._session_user(req)
        if username:
            return self._ok(f"Profile: {username}")
        return self._error(401, "Unauthorized", "You must log in to view this page.")

    def _account(self, req: HttpRequest) -> HttpResponse:
        """Cookie-protected page that redirects instead of erroring when
        unauthenticated (YC-035.3) — the browser-style counterpart to
        /profile's API-style 401, so students see both patterns real
        sites use for a "protected route"."""
        username = self._session_user(req)
        if username:
            return self._ok(f"Account settings for {username}.")
        return self._redirect("/login")

    def _dashboard(self, req: HttpRequest) -> HttpResponse:
        username = self._session_user(req)
        if username:
            return self._ok(f"Dashboard: welcome back, {username}.")
        return self._redirect("/login")

    def _admin(self, req: HttpRequest) -> HttpResponse:
        """Authentication vs. authorization (YC-035.3): an unauthenticated
        request is 401 ("who are you?"), but the training user "student",
        while fully authenticated, is still not "admin" — 403 ("you are
        known, but not allowed here"). Only "admin" (a fictional training
        account) may pass."""
        username = self._session_user(req)
        if username is None:
            return self._error(401, "Unauthorized", "You must log in to view this page.")
        if username != "admin":
            return self._json_error(
                403, "Forbidden",
                {"error": "Forbidden",
                 "message": "You are authenticated, but not authorized to access this resource."})
        return self._ok("Admin dashboard: training-site controls.")

    def _logout(self, req: HttpRequest) -> HttpResponse:
        """Invalidates the server-side session (YC-035.0) and, as of
        YC-035.3, tells the browser to delete the cookie too
        (`deleted_cookies`) — GET keeps its original Location ("/") for
        backward compatibility with earlier missions; POST (the form-submit
        flow this mission teaches) redirects to /login instead."""
        sid = req.cookies.get("session_id")
        if sid:
            self.sessions.pop(sid, None)
        location = "/login" if req.method == "POST" else "/"
        resp = self._redirect(location)
        resp.deleted_cookies.append("session_id")
        return resp

    def expire_session(self, sid: str) -> bool:
        """Simulator-controlled session expiration (YC-035.3) — deterministic
        and explicitly triggered (the 'expire' terminal command), never tied
        to real wall-clock time. Server-side this is identical to logout
        (the session stops being recognized), but nothing tells the
        browser to drop its cookie: the whole point is that the student's
        browser *still has* the stale session_id, yet the server now
        rejects it — visibly different from logout's explicit cookie
        deletion."""
        return self.sessions.pop(sid, None) is not None

    def _session_user(self, req: HttpRequest) -> str | None:
        """Cookie-based session lookup — the browser/HTML auth mechanism."""
        sid = req.cookies.get("session_id")
        return self.sessions.get(sid) if sid else None

    def _bearer_user(self, req: HttpRequest) -> str | None:
        """Authorization: Bearer <token> lookup — a deliberately separate,
        token-based mechanism (YC-035.1) so students see cookie-session
        auth and header-token auth as two distinct concepts, not the same
        thing wearing different clothes. Only the fixed training token
        maps to an identity; nothing here is a real auth system."""
        auth = req.headers.get("Authorization", "")
        if auth == f"Bearer {API_TOKEN}":
            return "student"
        return None

    def _api_login(self, req: HttpRequest) -> HttpResponse:
        username = self._check_credentials(req)
        if username:
            return self._json_ok({"status": "success", "message": "Authentication successful"})
        return self._json_error(401, "Unauthorized",
                                {"status": "error", "message": "Invalid credentials"})

    def _get_profile(self, username: str) -> dict[str, Any]:
        return self.profiles.setdefault(username, {"display_name": username})

    def _api_profile(self, req: HttpRequest) -> HttpResponse:
        """JSON counterpart to /profile — cookie-session protected, like
        the HTML page, to teach that a JSON API can sit behind the same
        session cookie (distinct from the bearer-token /api/me below).

        POST actually persists (YC-035.2), but only under the exact key
        'display_name' — a case-mismatched key (e.g. 'Display_Name') is
        silently ignored, matching real-world APIs that don't warn about
        unrecognized fields. Still returns 200 either way, so the bug is
        only visible by checking the field actually changed, not the
        status code — the crux of the mission's final investigation."""
        username = self._session_user(req)
        if not username:
            return self._json_error(401, "Unauthorized",
                                    {"status": "error", "message": "Authentication required"})
        profile = self._get_profile(username)
        if req.method == "POST":
            data = parse_body(req.body, req.headers.get("Content-Type", ""))
            if "display_name" in data:
                profile["display_name"] = data["display_name"]
            return self._json_ok({"status": "updated", "display_name": profile["display_name"]})
        return self._json_ok({"username": username, "display_name": profile["display_name"]})

    def _api_me(self, req: HttpRequest) -> HttpResponse:
        username = self._bearer_user(req)
        if username:
            return self._json_ok({"username": username})
        return self._json_error(401, "Unauthorized",
                                {"status": "error", "message": "Authentication required"})

    def _ok(self, body: str, content_type: str = "text/html") -> HttpResponse:
        return HttpResponse(status_code=200, reason="OK", body=body, content_type=content_type,
                            headers={"Content-Type": content_type, "Content-Length": str(len(body)),
                                    "Server": SERVER_HEADER, "Cache-Control": "no-store"})

    def _json_ok(self, data: dict[str, Any]) -> HttpResponse:
        body = json.dumps(data)
        return HttpResponse(status_code=200, reason="OK", body=body, content_type="application/json",
                            headers={"Content-Type": "application/json", "Content-Length": str(len(body)),
                                    "Server": SERVER_HEADER, "Cache-Control": "no-store"})

    def _json_error(self, code: int, reason: str, data: dict[str, Any]) -> HttpResponse:
        body = json.dumps(data)
        return HttpResponse(status_code=code, reason=reason, body=body, content_type="application/json",
                            headers={"Content-Type": "application/json", "Content-Length": str(len(body)),
                                    "Server": SERVER_HEADER})

    def _redirect(self, location: str) -> HttpResponse:
        return HttpResponse(status_code=302, reason="Found", content_type="text/plain",
                            headers={"Location": location, "Content-Length": "0",
                                    "Server": SERVER_HEADER})

    def _error(self, code: int, reason: str, message: str) -> HttpResponse:
        return HttpResponse(status_code=code, reason=reason, body=message, content_type="text/plain",
                            headers={"Content-Type": "text/plain", "Content-Length": str(len(message)),
                                    "Server": SERVER_HEADER})

    def _not_found(self) -> HttpResponse:
        return self._error(404, "Not Found", "The requested resource was not found.")


def build_investigation_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the final objective: a
    fictional user ("Alex") visits the login page but never actually
    submits the form, so no session is ever created and /profile
    correctly denies them. Built once against an isolated WebApp
    instance — never touches the student's own session state."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/login")
    req = build_request("GET", url, timestamp=1.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("GET", url, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/profile")
    req = build_request("GET", url, timestamp=3.0)  # no cookies — never logged in
    log.append((req, app.handle(req)))

    return log


def build_content_type_bug_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the HTTP Deep Dive final
    objective (YC-035.1): a user logs in *successfully* — form submitted,
    redirect followed, session cookie set and used — but their profile
    "loads incorrectly". The root cause is a benign misconfiguration, not
    an attack: the final response's Content-Type is wrong
    (application/json instead of text/html), even though the body and
    status code are otherwise correct. Built once against an isolated
    WebApp instance — never touches the student's own session state."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/login")
    req = build_request("GET", url, timestamp=1.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("GET", url, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("POST", url, body="username=student&password=training123", timestamp=3.0)
    resp = app.handle(req)
    log.append((req, resp))
    sid = resp.cookies["session_id"]

    url = parse_url(f"https://{HOST}/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=4.0)
    resp = app.handle(req)
    # The deliberate bug: right body, right status, wrong Content-Type —
    # the actual thing the student must notice and report.
    resp.headers["Content-Type"] = "application/json"
    resp.content_type = "application/json"
    log.append((req, resp))

    return log


def build_profile_mismatch_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the Burp Fundamentals final
    objective (YC-035.2): a user ("student") logs in, then tries to update
    their display name, but a client bug sends the field under the wrong
    key ('Display_Name' instead of 'display_name'). The server accepts
    the request (200 OK) but silently ignores the unrecognized field, so
    a follow-up GET still shows the old name — "profile information not
    displaying correctly", the fictional bug report. A benign HTTP
    parameter mismatch, not an attack. Built once against an isolated
    WebApp instance — never touches the student's own session state."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("POST", url, body="username=student&password=training123", timestamp=1.0)
    resp = app.handle(req)
    log.append((req, resp))
    sid = resp.cookies["session_id"]

    url = parse_url(f"https://{HOST}/api/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/api/profile")
    req = build_request("POST", url, body='{"Display_Name": "Alex Rivera"}',
                        cookies={"session_id": sid},
                        extra_headers={"Content-Type": "application/json"}, timestamp=3.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/api/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=4.0)
    log.append((req, app.handle(req)))

    return log


def build_auth_lifecycle_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the Authentication & Sessions
    final objective (YC-035.3): a student reports "I logged in fine, but
    after I logged out I can't get back into my profile" — as if that were
    a bug. It isn't: the transcript shows a completely correct lifecycle —
    successful login, an authenticated /profile hit, an explicit logout
    (which deletes the session cookie server-side), then a final /profile
    request that is correctly denied because the session no longer exists.
    The "investigation" is realizing logout is supposed to do that. Built
    once against an isolated WebApp instance — never touches the student's
    own session state."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("POST", url, body="username=student&password=training123", timestamp=1.0)
    resp = app.handle(req)
    log.append((req, resp))
    sid = resp.cookies["session_id"]

    url = parse_url(f"https://{HOST}/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/logout")
    req = build_request("POST", url, cookies={"session_id": sid}, timestamp=3.0)
    log.append((req, app.handle(req)))

    # The browser's cookie jar would have discarded session_id after the
    # deletion above; this final request models what happens if it's sent
    # anyway (e.g. a stale tab) — still correctly rejected, since the
    # server-side session is gone either way.
    url = parse_url(f"https://{HOST}/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=4.0)
    log.append((req, app.handle(req)))

    return log


_INVESTIGATION_BUILDERS: dict[str, Callable[[], list[tuple[HttpRequest, HttpResponse]]]] = {
    "login-flow": build_investigation_log,
    "content-type-bug": build_content_type_bug_log,
    "profile-mismatch": build_profile_mismatch_log,
    "auth-lifecycle": build_auth_lifecycle_log,
}


@dataclass
class WebSession:
    """The student's own client-side state: cookie jar + request history."""
    cookies: dict[str, str] = field(default_factory=dict)
    history: list[tuple[HttpRequest, HttpResponse]] = field(default_factory=list)

    @property
    def last_request(self) -> HttpRequest | None:
        return self.history[-1][0] if self.history else None

    @property
    def last_response(self) -> HttpResponse | None:
        return self.history[-1][1] if self.history else None

    def record(self, req: HttpRequest, resp: HttpResponse) -> None:
        self.history.append((req, resp))
        for k, v in resp.cookies.items():
            self.cookies[k] = v
        # Logout's Set-Cookie deletion (YC-035.3) — the browser drops the
        # cookie from its own jar exactly as it would apply any other
        # Set-Cookie instruction from the server.
        for k in resp.deleted_cookies:
            self.cookies.pop(k, None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cookies": self.cookies,
            "history": [[dataclasses.asdict(r), dataclasses.asdict(s)]
                       for r, s in self.history[-20:]],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WebSession:
        ws = cls()
        ws.cookies = d.get("cookies", {})
        ws.history = [(HttpRequest(**r), HttpResponse(**s)) for r, s in d.get("history", [])]
        return ws


@dataclass
class ProxyState:
    """Intercepting-proxy state for a WebLab session (YC-035.2) — mirrors
    WebSession's shape: small, explicit, mutable, in-memory only. Every
    counter here backs a structured validator check (mission_validator.py)
    instead of matching rendered text, per the project's established
    'do not validate by brittle string matching' discipline."""
    intercept_enabled: bool = False
    pending: HttpRequest | None = None
    intercepted_count: int = 0
    forwarded_count: int = 0
    dropped_count: int = 0
    blocked_count: int = 0
    repeater_request: HttpRequest | None = None
    repeater_loaded_count: int = 0
    repeater_sent_count: int = 0
    compared_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "intercept_enabled": self.intercept_enabled,
            "pending": dataclasses.asdict(self.pending) if self.pending else None,
            "intercepted_count": self.intercepted_count,
            "forwarded_count": self.forwarded_count,
            "dropped_count": self.dropped_count,
            "blocked_count": self.blocked_count,
            "repeater_request": dataclasses.asdict(self.repeater_request)
                if self.repeater_request else None,
            "repeater_loaded_count": self.repeater_loaded_count,
            "repeater_sent_count": self.repeater_sent_count,
            "compared_count": self.compared_count,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProxyState:
        ps = cls()
        ps.intercept_enabled = d.get("intercept_enabled", False)
        ps.pending = HttpRequest(**d["pending"]) if d.get("pending") else None
        ps.intercepted_count = d.get("intercepted_count", 0)
        ps.forwarded_count = d.get("forwarded_count", 0)
        ps.dropped_count = d.get("dropped_count", 0)
        ps.blocked_count = d.get("blocked_count", 0)
        ps.repeater_request = HttpRequest(**d["repeater_request"]) if d.get("repeater_request") else None
        ps.repeater_loaded_count = d.get("repeater_loaded_count", 0)
        ps.repeater_sent_count = d.get("repeater_sent_count", 0)
        ps.compared_count = d.get("compared_count", 0)
        return ps


class WebLab:
    """Everything a web-fundamentals mission session needs: the
    simulated site, the student's own session, the fixed investigation
    transcript for the final objective, and (YC-035.2) intercepting-proxy
    state. `proxy` costs nothing for missions that never touch it (its
    counters simply stay at their defaults) so YC-035.0/YC-035.1 are
    unaffected."""

    def __init__(self, app: WebApp, investigation_log: list[tuple[HttpRequest, HttpResponse]]) -> None:
        self.app = app
        self.session = WebSession()
        self.investigation_log = investigation_log
        self.proxy = ProxyState()
        # Counts uses of the 'expire' command (YC-035.3) — deliberately a
        # simple counter, mirroring ProxyState's counters, rather than a
        # new dataclass for a single field. Distinguishes "this session
        # became invalid because the student explicitly expired it" from
        # "because they logged out", for the session_expired validator
        # check.
        self.expired_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {"sessions": dict(self.app.sessions), "profiles": dict(self.app.profiles),
                "session": self.session.to_dict(), "proxy": self.proxy.to_dict(),
                "expired_count": self.expired_count}

    def apply_state(self, snapshot: dict[str, Any]) -> None:
        self.app.sessions = dict(snapshot.get("sessions", {}))
        self.app.profiles = dict(snapshot.get("profiles", {}))
        self.session = WebSession.from_dict(snapshot.get("session", {}))
        self.proxy = ProxyState.from_dict(snapshot.get("proxy", {}))
        self.expired_count = snapshot.get("expired_count", 0)


def build_web_lab(scenario: str = "login-flow") -> WebLab:
    """`scenario` selects which fixed investigation transcript this
    mission's final objective gets (YC-035.1 needs a different one than
    YC-035.0), the same registry pattern as packets.py's CAPTURE_REGISTRY."""
    builder = _INVESTIGATION_BUILDERS.get(scenario, build_investigation_log)
    return WebLab(app=WebApp(), investigation_log=builder())


# ── Rendering — text formatting only ──
def render_request(req: HttpRequest) -> str:
    target = req.path
    if req.query:
        target += "?" + "&".join(f"{k}={v}" for k, v in req.query.items())
    lines = [f"{req.method} {target} HTTP/1.1"]
    for k, v in req.headers.items():
        lines.append(f"{k}: {v}")
    if req.cookies:
        lines.append("Cookie: " + "; ".join(f"{k}={v}" for k, v in req.cookies.items()))
    if req.body:
        lines.append("")
        lines.append(req.body)
    return "\n".join(lines)


def render_response(resp: HttpResponse) -> str:
    lines = [f"HTTP/1.1 {resp.status_code} {resp.reason}"]
    for k, v in resp.headers.items():
        lines.append(f"{k}: {v}")
    for k, v in resp.cookies.items():
        lines.append(f"Set-Cookie: {k}={v}")
    for k in resp.deleted_cookies:
        lines.append(f"Set-Cookie: {k}=; Max-Age=0")
    if resp.body:
        lines.append("")
        lines.append(resp.body)
    return "\n".join(lines)


def render_exchange(req: HttpRequest, resp: HttpResponse) -> str:
    return ("━━━━━━━━ REQUEST ━━━━━━━━\n"
           + render_request(req)
           + "\n\n━━━━━━━━ RESPONSE ━━━━━━━━\n"
           + render_response(resp))
