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
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlsplit

HOST = "cybershop.training"
SERVER_HEADER = "CyberShop-Sim/1.0"

# Training-only credentials — never real accounts.
_USERS = {"student": "training123", "analyst": "analyst123", "admin": "admin123"}


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
    body: str = ""
    content_type: str = "text/plain"
    server: str = SERVER_HEADER


def build_request(method: str, url: ParsedUrl, body: str = "",
                  cookies: dict[str, str] | None = None,
                  timestamp: float = 0.0) -> HttpRequest:
    headers = {
        "Host": url.host,
        "User-Agent": "YushaCyber-Trainer/1.0",
        "Accept": "*/*",
    }
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Content-Length"] = str(len(body))
    return HttpRequest(method=method.upper(), scheme=url.scheme, host=url.host,
                       port=url.port, path=url.path, query=dict(url.query),
                       headers=headers, cookies=dict(cookies or {}), body=body,
                       timestamp=timestamp)


class WebApp:
    """The simulated CyberShop training site. Routes are plain Python
    control flow over deterministic canned responses — never a real
    server, never a real socket."""

    def __init__(self, sessions: dict[str, str] | None = None) -> None:
        # session_id -> username. Mutated by successful logins/logouts,
        # exactly like VirtualNetwork's interface state (YC-034.6) —
        # small, explicit, session-scoped state.
        self.sessions: dict[str, str] = dict(sessions) if sessions else {}

    def handle(self, req: HttpRequest) -> HttpResponse:
        if req.path == "/" and req.method == "GET":
            return self._ok("Welcome to CyberShop — a simulated training storefront.")
        if req.path == "/products" and req.method == "GET":
            pid = req.query.get("id")
            if pid:
                return self._ok(f"Product #{pid}: Sample training item.")
            return self._ok("Product catalog: 3 items available.")
        if req.path == "/search" and req.method == "GET":
            q = req.query.get("q", "")
            return self._ok(f"Search results for '{q}': 0 matches in the training catalog.")
        if req.path == "/login" and req.method == "GET":
            return self._redirect("/auth/login")
        if req.path == "/auth/login" and req.method == "GET":
            return self._ok("Please log in with your training account.")
        if req.path == "/login" and req.method == "POST":
            return self._login(req)
        if req.path == "/profile" and req.method == "GET":
            return self._profile(req)
        if req.path == "/logout" and req.method == "GET":
            return self._logout(req)
        return self._not_found()

    def _login(self, req: HttpRequest) -> HttpResponse:
        form = _parse_form(req.body)
        username, password = form.get("username", ""), form.get("password", "")
        if username in _USERS and _USERS[username] == password:
            sid = f"{username}-session"
            self.sessions[sid] = username
            resp = self._redirect("/profile")
            resp.cookies["session_id"] = sid
            return resp
        return self._error(401, "Unauthorized", "Invalid username or password.")

    def _profile(self, req: HttpRequest) -> HttpResponse:
        sid = req.cookies.get("session_id")
        username = self.sessions.get(sid) if sid else None
        if username:
            return self._ok(f"Profile: {username}")
        return self._error(401, "Unauthorized", "You must log in to view this page.")

    def _logout(self, req: HttpRequest) -> HttpResponse:
        sid = req.cookies.get("session_id")
        if sid:
            self.sessions.pop(sid, None)
        return self._redirect("/")

    def _ok(self, body: str, content_type: str = "text/html") -> HttpResponse:
        return HttpResponse(status_code=200, reason="OK", body=body, content_type=content_type,
                            headers={"Content-Type": content_type, "Content-Length": str(len(body)),
                                    "Server": SERVER_HEADER, "Cache-Control": "no-store"})

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


class WebLab:
    """Everything a web-fundamentals mission session needs: the
    simulated site, the student's own session, and the fixed
    investigation transcript for the final objective."""

    def __init__(self, app: WebApp, investigation_log: list[tuple[HttpRequest, HttpResponse]]) -> None:
        self.app = app
        self.session = WebSession()
        self.investigation_log = investigation_log

    def to_dict(self) -> dict[str, Any]:
        return {"sessions": dict(self.app.sessions), "session": self.session.to_dict()}

    def apply_state(self, snapshot: dict[str, Any]) -> None:
        self.app.sessions = dict(snapshot.get("sessions", {}))
        self.session = WebSession.from_dict(snapshot.get("session", {}))


def build_web_lab() -> WebLab:
    return WebLab(app=WebApp(), investigation_log=build_investigation_log())


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
    if resp.body:
        lines.append("")
        lines.append(resp.body)
    return "\n".join(lines)


def render_exchange(req: HttpRequest, resp: HttpResponse) -> str:
    return ("━━━━━━━━ REQUEST ━━━━━━━━\n"
           + render_request(req)
           + "\n\n━━━━━━━━ RESPONSE ━━━━━━━━\n"
           + render_response(resp))
