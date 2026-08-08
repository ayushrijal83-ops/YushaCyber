"""Simulated Burp-style intercepting proxy — YC-035.2 Burp Suite
Fundamentals.

Sits conceptually in front of the same simulated CyberShop site built for
YC-035.0/YC-035.1 (`web.py`'s `WebApp`), reusing its `HttpRequest`/
`HttpResponse` dataclasses and `build_request`/`parse_url` helpers
unchanged — there is no second HTTP model and no second simulated
server. This module only adds the state a real intercepting proxy
teaches: intercept on/off, one paused pending request, forward, drop,
in-place editing, proxy history, a Repeater workspace, response
comparison, and scope enforcement.

Like `web.py`, this is pure in-memory dataclasses and string handling —
no outbound HTTP client anywhere (no `socket`, `requests`,
`urllib.request`, `http.client`). Every request this module ever
constructs is handled by the in-process `WebApp.handle()`; nothing here
could reach a real host even if a caller tried.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from app.core.terminal.web import HOST, HttpRequest, HttpResponse, WebApp

# The only host the simulated proxy will ever forward a request to —
# the training site itself. Anything else is a scope violation.
SCOPE_HOST = HOST


def _copy_request(req: HttpRequest) -> HttpRequest:
    """A shallow-safe copy — new dicts for the mutable fields — so editing
    a Repeater draft or a resent request never mutates an entry already
    recorded in history."""
    return dataclasses.replace(
        req, query=dict(req.query), headers=dict(req.headers), cookies=dict(req.cookies))


@dataclass
class ProxyLab:
    """One student's proxy session: the simulated server, intercept
    state, forwarded-request history, Repeater workspace, and the
    scope-violation log — the Burp-mission counterpart to `WebLab`."""

    app: WebApp = field(default_factory=WebApp)
    cookies: dict[str, str] = field(default_factory=dict)

    intercept_enabled: bool = False
    pending_request: HttpRequest | None = None
    # Kept even after the pending request is forwarded/dropped, so an
    # objective can still ask "was this ever intercepted?" after the fact.
    last_intercepted: HttpRequest | None = None

    history: list[tuple[HttpRequest, HttpResponse]] = field(default_factory=list)
    last_dropped: HttpRequest | None = None
    dropped_count: int = 0

    repeater_request: HttpRequest | None = None
    repeater_log: list[tuple[HttpRequest, HttpResponse]] = field(default_factory=list)
    compared: bool = False
    last_comparison: str = ""

    # Hostnames a "browse" attempt tried to reach outside the training
    # scope (cybershop.training) — never turned into a request object.
    blocked_hosts: list[str] = field(default_factory=list)

    @property
    def last_request(self) -> HttpRequest | None:
        return self.history[-1][0] if self.history else None

    @property
    def last_response(self) -> HttpResponse | None:
        return self.history[-1][1] if self.history else None

    def in_scope(self, host: str) -> bool:
        return host == SCOPE_HOST

    # ── Browser → Proxy ──
    def intercept(self, req: HttpRequest) -> None:
        """Pause a request in the proxy instead of forwarding it."""
        self.pending_request = req
        self.last_intercepted = req

    def dispatch(self, req: HttpRequest) -> HttpResponse:
        """Send straight through (Intercept is OFF) — recorded in history
        exactly like a forwarded request, since nothing paused it."""
        resp = self.app.handle(req)
        self._record(req, resp)
        return resp

    def _record(self, req: HttpRequest, resp: HttpResponse) -> None:
        self.history.append((req, resp))
        for k, v in resp.cookies.items():
            self.cookies[k] = v

    # ── Intercept panel actions ──
    def forward_pending(self) -> HttpResponse | None:
        if self.pending_request is None:
            return None
        req = self.pending_request
        self.pending_request = None
        resp = self.app.handle(req)
        self._record(req, resp)
        return resp

    def drop_pending(self) -> bool:
        if self.pending_request is None:
            return False
        self.last_dropped = self.pending_request
        self.dropped_count += 1
        self.pending_request = None
        return True

    def edit_pending(self, method: str | None = None, path: str | None = None,
                     query: dict[str, str] | None = None,
                     headers: dict[str, str] | None = None,
                     body: str | None = None) -> bool:
        return self._edit(self.pending_request, method, path, query, headers, body)

    @staticmethod
    def _edit(req: HttpRequest | None, method: str | None, path: str | None,
              query: dict[str, str] | None, headers: dict[str, str] | None,
              body: str | None) -> bool:
        if req is None:
            return False
        if method:
            req.method = method.upper()
        if path:
            req.path = path
        if query:
            req.query.update(query)
        if headers:
            req.headers.update(headers)
        if body is not None:
            req.body = body
            req.headers["Content-Length"] = str(len(body))
        return True

    # ── HTTP history ──
    def history_contains(self, method: str, path: str) -> bool:
        return any(r.method == method.upper() and r.path == path for r, _ in self.history)

    # ── Repeater ──
    def send_to_repeater(self, index: int) -> bool:
        """Copy history[index] (1-based) into the Repeater as an editable
        draft — a deep-ish copy so later edits never mutate the original
        history entry."""
        if not (1 <= index <= len(self.history)):
            return False
        req, _ = self.history[index - 1]
        self.repeater_request = _copy_request(req)
        return True

    def edit_repeater(self, method: str | None = None, path: str | None = None,
                      query: dict[str, str] | None = None,
                      headers: dict[str, str] | None = None,
                      body: str | None = None) -> bool:
        return self._edit(self.repeater_request, method, path, query, headers, body)

    def send_repeater(self) -> HttpResponse | None:
        if self.repeater_request is None:
            return None
        sent = self.repeater_request
        resp = self.app.handle(sent)
        self.repeater_log.append((sent, resp))
        # Further edits start from a fresh copy — never mutate a sent entry.
        self.repeater_request = _copy_request(sent)
        return resp

    def compare(self, a: int, b: int) -> str | None:
        """A simple line-based comparison of two Repeater responses
        (1-based indices into repeater_log) — deliberately not a real
        diff engine."""
        if not (1 <= a <= len(self.repeater_log)) or not (1 <= b <= len(self.repeater_log)):
            return None
        resp_a, resp_b = self.repeater_log[a - 1][1], self.repeater_log[b - 1][1]
        lines_a = resp_a.body.splitlines() or [""]
        lines_b = resp_b.body.splitlines() or [""]
        out = [f"Response #{a}: {resp_a.status_code} {resp_a.reason}",
              f"Response #{b}: {resp_b.status_code} {resp_b.reason}", ""]
        differed = resp_a.status_code != resp_b.status_code
        if differed:
            out.append(f"- Status differs: {resp_a.status_code} vs {resp_b.status_code}")
        for i in range(max(len(lines_a), len(lines_b))):
            la = lines_a[i] if i < len(lines_a) else "(missing)"
            lb = lines_b[i] if i < len(lines_b) else "(missing)"
            if la != lb:
                differed = True
                out.append(f"- Line {i + 1} differs:")
                out.append(f"    A: {la}")
                out.append(f"    B: {lb}")
        if not differed:
            out.append("No meaningful differences found.")
        self.compared = True
        self.last_comparison = "\n".join(out)
        return self.last_comparison

    # ── Persistence ──
    def to_dict(self) -> dict[str, Any]:
        return {
            "cookies": self.cookies,
            "sessions": dict(self.app.sessions),
            "intercept_enabled": self.intercept_enabled,
            "pending_request": dataclasses.asdict(self.pending_request) if self.pending_request else None,
            "last_intercepted": dataclasses.asdict(self.last_intercepted) if self.last_intercepted else None,
            "history": [[dataclasses.asdict(r), dataclasses.asdict(s)]
                       for r, s in self.history[-30:]],
            "last_dropped": dataclasses.asdict(self.last_dropped) if self.last_dropped else None,
            "dropped_count": self.dropped_count,
            "repeater_request": dataclasses.asdict(self.repeater_request) if self.repeater_request else None,
            "repeater_log": [[dataclasses.asdict(r), dataclasses.asdict(s)]
                            for r, s in self.repeater_log[-20:]],
            "compared": self.compared,
            "last_comparison": self.last_comparison,
            "blocked_hosts": list(self.blocked_hosts[-10:]),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProxyLab:
        lab = cls()
        lab.cookies = d.get("cookies", {})
        lab.app.sessions = dict(d.get("sessions", {}))
        lab.intercept_enabled = d.get("intercept_enabled", False)
        lab.pending_request = HttpRequest(**d["pending_request"]) if d.get("pending_request") else None
        lab.last_intercepted = HttpRequest(**d["last_intercepted"]) if d.get("last_intercepted") else None
        lab.history = [(HttpRequest(**r), HttpResponse(**s)) for r, s in d.get("history", [])]
        lab.last_dropped = HttpRequest(**d["last_dropped"]) if d.get("last_dropped") else None
        lab.dropped_count = d.get("dropped_count", 0)
        lab.repeater_request = HttpRequest(**d["repeater_request"]) if d.get("repeater_request") else None
        lab.repeater_log = [(HttpRequest(**r), HttpResponse(**s)) for r, s in d.get("repeater_log", [])]
        lab.compared = d.get("compared", False)
        lab.last_comparison = d.get("last_comparison", "")
        lab.blocked_hosts = list(d.get("blocked_hosts", []))
        return lab


def build_proxy_lab() -> ProxyLab:
    return ProxyLab()
