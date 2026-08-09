"""Mission validator — checks objectives against terminal state.

Reuses the terminal shell state to validate objectives automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.terminal.shell import Shell


@dataclass
class ValidationResult:
    passed: bool = False
    objective_id: str = ""
    message: str = ""
    xp: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "objective_id": self.objective_id,
                "message": self.message, "xp": self.xp}


def _match_candidates(raw_match: Any) -> list[str]:
    """A 'match' value is normally one string, but may be a list of
    acceptable alternatives (YC-034.8) — e.g. "any of these three hosts
    counts as evidence", not just one hardcoded exact command. Lets a
    validator check the *meaning* of a result instead of one literal
    string, while staying a plain data field (no new validator type)."""
    if isinstance(raw_match, (list, tuple)):
        return [str(m).strip() for m in raw_match]
    return [str(raw_match).strip()]


def validate(objective: dict[str, Any], shell: Shell,
             command: str = "", output: str = "") -> ValidationResult:
    """Validate an objective against the current shell state."""
    v = objective.get("validate", {})
    v_type = v.get("type", "command")
    candidates = _match_candidates(v.get("match", ""))
    expected = candidates[0]
    obj_id = objective.get("id", "")
    xp = objective.get("xp", 0)

    if v_type == "command":
        cmd_lower = command.strip().lower()
        if any(cmd_lower == c.lower() or c.lower() in cmd_lower for c in candidates):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Try a different command.")

    if v_type == "cwd":
        if shell.fs.cwd == expected or shell.fs.abspath(".") == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Navigate to {expected} first.")

    if v_type == "file_exists":
        if shell.fs.isfile(expected):
            return _pass(obj_id, xp)
        return _fail(obj_id, f"File '{expected.split('/')[-1]}' not found yet.")

    if v_type == "dir_exists":
        if shell.fs.isdir(expected):
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Directory '{expected.split('/')[-1]}' not found yet.")

    if v_type == "file_contains":
        content = (shell.fs.read(v.get("path", "")) or "").lower()
        if any(c.lower() in content for c in candidates):
            return _pass(obj_id, xp)
        return _fail(obj_id, "File doesn't contain the expected content.")

    if v_type == "output_contains":
        out_lower = output.lower()
        if any(c.lower() in out_lower for c in candidates):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Output doesn't contain what's expected.")

    if v_type == "file_mode":
        path = v.get("path", "")
        if shell.fs.get_mode(path) == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"'{path.split('/')[-1]}' doesn't have the expected permissions yet.")

    if v_type == "file_owner":
        path = v.get("path", "")
        if shell.fs.get_owner(path) == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"'{path.split('/')[-1]}' isn't owned by the expected user yet.")

    if v_type == "network_state":
        return _validate_network_state(v, shell, obj_id, xp, expected)

    if v_type == "web_state":
        return _validate_web_state(v, shell, obj_id, xp, expected)

    return _fail(obj_id, "Unknown validation type.")


def _validate_network_state(v: dict[str, Any], shell: Shell, obj_id: str,
                            xp: int, expected: str) -> ValidationResult:
    """Checks actual (mutable) simulated-network state — reusable by any
    mission whose network can change (chmod/chown's counterpart for the
    network simulator). Only meaningful once a mission can mutate state;
    see YC-034.6."""
    net = getattr(shell, "network", None)
    if net is None:
        return _fail(obj_id, "No simulated network available.")
    check = v.get("check")

    if check == "interface_state":
        iface = v.get("interface", "eth0")
        state = next((i.state for i in net.student.interfaces if i.name == iface), None)
        if state == expected.upper():
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Interface {iface} isn't {expected.upper()} yet.")

    if check == "interface_ip":
        iface = v.get("interface", "eth0")
        ip = next((i.ip for i in net.student.interfaces if i.name == iface), None)
        if ip == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Interface {iface} doesn't have the expected address yet.")

    if check == "default_gateway":
        if net.default_gateway() == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, "The default gateway isn't set correctly yet.")

    return _fail(obj_id, "Unknown network check.")


def _validate_web_state(v: dict[str, Any], shell: Shell, obj_id: str,
                        xp: int, expected: str) -> ValidationResult:
    """Checks structured HTTP request/response state (YC-035.0) — the
    web-mission counterpart to _validate_network_state. Used wherever a
    specific factual answer (a status code, a header value, a cookie)
    should be checked against real simulator state rather than a
    substring of rendered text, per the ticket's explicit instruction to
    avoid brittle string matching where structured data is available."""
    lab = getattr(shell, "web_lab", None)
    if lab is None:
        return _fail(obj_id, "No simulated web session available.")
    check = v.get("check")
    req, resp = lab.session.last_request, lab.session.last_response

    if check == "status_code":
        if resp is not None and str(resp.status_code) == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, "That status code hasn't been observed yet.")

    if check == "method":
        if req is not None and req.method == expected.upper():
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Try making a {expected.upper()} request.")

    if check == "path":
        if req is not None and req.path == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Request {expected} to see this.")

    if check == "query_param":
        param = v.get("param", "")
        if req is not None and req.query.get(param) == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Check the '{param}' query parameter.")

    if check == "header":
        name = v.get("header", "")
        in_ = v.get("in", "response")
        source = req if in_ == "request" else resp
        value = source.headers.get(name) if source else None
        if value is not None and value.lower() == expected.lower():
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Check the '{name}' {in_} header.")

    if check == "cookie":
        name = v.get("cookie_name", "session_id")
        if lab.session.cookies.get(name) == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"The '{name}' cookie doesn't have the expected value yet.")

    if check == "redirect_location":
        if resp is not None and resp.status_code in (301, 302) \
                and resp.headers.get("Location") == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, "Look for a redirect response and check its Location header.")

    if check == "body_field":
        # Inspects a specific JSON/form field on the request or response
        # body (YC-035.1) — structured, so a student can't pass by having
        # *any* text containing the expected value somewhere unrelated.
        field_name = v.get("field", "")
        in_ = v.get("in", "response")
        source = req if in_ == "request" else resp
        if source is None:
            return _fail(obj_id, "No body to inspect yet.")
        from app.core.terminal.web import parse_body
        data = parse_body(source.body, source.headers.get("Content-Type", ""))
        if str(data.get(field_name, "")) == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Check the '{field_name}' field in the {in_} body.")

    if check == "history_sequence":
        # `sequence` (a list, via the existing match-list mechanism) is
        # read here as an *ordered* list of "METHOD path" tokens that
        # must appear in the session's own request history, in that
        # order — not necessarily contiguous, so following a redirect via
        # extra intermediate requests still counts.
        sequence = _match_candidates(v.get("match", ""))
        hist_tokens = [f"{r.method} {r.path}" for r, _ in lab.session.history]
        idx = 0
        for token in hist_tokens:
            if idx < len(sequence) and token == sequence[idx]:
                idx += 1
        if idx >= len(sequence):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Make the requests in this chain, in order.")

    if check == "request_count":
        if len(lab.session.history) >= int(expected):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Make a few more requests first.")

    # ── Intercepting proxy checks (YC-035.2 — Burp Suite Fundamentals).
    # Each reads a counter/flag off WebLab.proxy (ProxyState, web.py) —
    # structured state, not rendered text, matching every check above.
    if check == "proxy_enabled":
        if lab.proxy.intercept_enabled == (expected.lower() == "true"):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Turn intercept on with 'intercept on'.")

    if check == "request_intercepted":
        if lab.proxy.intercepted_count >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Turn intercept on, then make a request to capture it.")

    if check == "request_forwarded":
        if lab.proxy.forwarded_count >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Intercept a request, then use 'forward'.")

    if check == "request_dropped":
        if lab.proxy.dropped_count >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Intercept a request, then use 'drop'.")

    if check == "repeater_used":
        if lab.proxy.repeater_loaded_count >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send a request to Repeater with 'repeater' or 'repeater N'.")

    if check == "repeater_sent":
        if lab.proxy.repeater_sent_count >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Load a request into Repeater, then use 'repeater send'.")

    if check == "response_compared":
        if lab.proxy.compared_count >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Compare two history entries with 'compare N M'.")

    if check == "scope_blocked":
        if lab.proxy.blocked_count >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Try requesting a host outside the training scope.")

    # ── Authentication & Sessions (YC-035.3). Each reads structured
    # request/response/session state exactly like the checks above — no
    # brittle text matching, matching this file's established discipline.
    if check == "cookie_sent":
        # Distinct from the 'cookie' check above: that one inspects the
        # *client-side jar* (lab.session.cookies) — "did I ever receive
        # this cookie?" This inspects the *last request actually sent*
        # (req.cookies) — "did my browser attach it to a request?" The
        # two can differ (a cookie can sit in the jar unused).
        name = v.get("cookie_name", "session_id")
        if req is not None and req.cookies.get(name) == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Make a request that carries the '{name}' cookie.")

    if check == "logout_completed":
        name = v.get("cookie_name", "session_id")
        if (req is not None and req.path == "/logout"
                and resp is not None and resp.status_code in (301, 302)
                and name in resp.deleted_cookies):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Log out and check the response for a Set-Cookie deletion.")

    if check == "session_expired":
        if lab.expired_count >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Use the 'expire' command to expire your session first.")

    if check == "session_authenticated":
        # Deliberately requires the *last request* to actually be a
        # successful hit on a session-gated resource — not just "a valid
        # cookie currently sits in the jar" (true immediately after
        # login, before the student ever exercises it against anything).
        sid = lab.session.cookies.get("session_id")
        authenticated = bool(
            sid and sid in lab.app.sessions
            and req is not None and resp is not None
            and resp.status_code == 200 and "session_id" in req.cookies
        )
        if authenticated == (expected.lower() == "true"):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Request a session-protected page while logged in.")

    return _fail(obj_id, "Unknown web check.")


def _pass(obj_id: str, xp: int) -> ValidationResult:
    return ValidationResult(passed=True, objective_id=obj_id,
                            message="✓ Objective Complete!", xp=xp)


def _fail(obj_id: str, msg: str) -> ValidationResult:
    return ValidationResult(passed=False, objective_id=obj_id,
                            message=msg)
