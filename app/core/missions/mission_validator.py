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

    # ── SQL Injection Fundamentals (YC-035.4). Each check reads either
    # the last request/response's structured 'X-Sim-Query-Kind' header
    # (set deterministically by WebApp's fixed training routes — see
    # web.py) or a counter/flag off WebLab.sqli (SqliLabState) — never
    # rendered text, matching this file's established discipline.
    if check == "normal_request":
        param = v.get("param", "q")
        kind = resp.headers.get("X-Sim-Query-Kind") if resp else None
        if (req is not None and req.path == "/search" and kind == "normal"
                and req.query.get(param, "").strip().lower() == expected.lower()):
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Search for '{expected}' with a plain, literal query.")

    if check == "error_observed":
        if (resp is not None and resp.status_code == 500
                and resp.headers.get("X-Sim-Query-Kind") == "error"):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send the malformed training input to /search and check the status code.")

    if check == "boolean_true_observed":
        if resp is not None and resp.headers.get("X-Sim-Query-Kind") == "boolean_true":
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send the TRUE training condition to /search.")

    if check == "boolean_false_observed":
        if resp is not None and resp.headers.get("X-Sim-Query-Kind") == "boolean_false":
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send the FALSE training condition to /search.")

    if check == "response_difference":
        if lab.sqli.boolean_true_seen and lab.sqli.boolean_false_seen:
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send both the TRUE and FALSE training conditions, then compare the results.")

    if check == "query_structure_inspected":
        if lab.sqli.query_inspections >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Use the 'query' command to inspect the simulated query representation.")

    if check == "training_auth_scenario":
        if expected.lower() == "bypassed":
            if lab.sqli.auth_bypass_triggered:
                return _pass(obj_id, xp)
            return _fail(obj_id, "Trigger the predefined authentication-bypass training pattern "
                                "on /training-login.")
        if req is not None and req.path == "/training-login" and req.method == "POST":
            return _pass(obj_id, xp)
        return _fail(obj_id, "POST to /training-login with the training credentials first.")

    if check == "secure_endpoint_tested":
        endpoint = v.get("endpoint", "/secure-search")
        tested = (lab.sqli.secure_search_tested if endpoint == "/secure-search"
                  else lab.sqli.secure_login_tested)
        if tested:
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Send the same training input to {endpoint}.")

    if check == "parameterized_query_identified":
        structural_change_seen = lab.sqli.boolean_true_seen or lab.sqli.boolean_false_seen
        if structural_change_seen and lab.sqli.secure_search_tested:
            return _pass(obj_id, xp)
        return _fail(obj_id, "Test the same training input against both /search and /secure-search, "
                            "then compare the simulated query representation.")

    if check == "evidence_collected":
        s = lab.sqli
        if (s.boolean_true_seen and s.boolean_false_seen
                and s.secure_search_tested and s.query_inspections > 0):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Collect more evidence: the TRUE/FALSE comparison, the query "
                            "representation ('query'), and the secure endpoint result.")

    # ── XSS Fundamentals (YC-035.5). Each check reads either the last
    # request/response's structured 'X-Sim-XSS-Kind'/'X-Sim-XSS-Context'
    # headers (set deterministically by WebApp's fixed training routes —
    # see web.py) or a flag off WebLab.xss (XssLabState) — never rendered
    # text, matching this file's established discipline.
    if check == "reflected_input":
        if resp is not None and resp.headers.get("X-Sim-XSS-Kind") == "reflected":
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send the training marker to /search as the 'q' parameter.")

    if check == "html_context":
        if resp is not None and resp.headers.get("X-Sim-XSS-Context") == expected:
            return _pass(obj_id, xp)
        return _fail(obj_id, "Check the X-Sim-XSS-Context header on your last response.")

    if check == "simulated_xss_event":
        if resp is not None and resp.headers.get("X-Sim-XSS-Kind") in ("reflected", "stored", "dom"):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Trigger one of the training markers first.")

    if check == "stored_input":
        stage = expected.lower()
        kind = resp.headers.get("X-Sim-XSS-Kind") if resp else None
        if stage == "submitted":
            if req is not None and req.path == "/feedback" and req.method == "POST" and kind == "stored":
                return _pass(obj_id, xp)
            return _fail(obj_id, "POST to /feedback with the training marker in the 'comment' field.")
        if stage == "displayed":
            if req is not None and req.path == "/comments" and kind == "stored":
                return _pass(obj_id, xp)
            return _fail(obj_id, "Open /comments after submitting the training marker.")
        return _fail(obj_id, "Unknown stage.")

    if check == "reflected_vs_stored":
        if lab.xss.reflected_seen and lab.xss.stored_seen:
            return _pass(obj_id, xp)
        return _fail(obj_id, "Trigger both the reflected (/search) and stored (/feedback + "
                            "/comments) training markers first.")

    if check == "dom_source":
        if req is not None and req.path == "/dom-demo":
            return _pass(obj_id, xp)
        return _fail(obj_id, "Open /dom-demo first.")

    if check == "dom_sink":
        if resp is not None and resp.headers.get("X-Sim-XSS-Kind") == "dom":
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send the training marker to /dom-demo as the 'input' parameter.")

    if check == "secure_encoding":
        target = v.get("endpoint", "/secure-search")
        if (req is not None and req.path == target
                and resp is not None and resp.headers.get("X-Sim-XSS-Kind") == "encoded"):
            return _pass(obj_id, xp)
        return _fail(obj_id, f"Send the same training marker to {target}.")

    if check == "html_escaped_observed":
        if resp is not None and "&lt;" in resp.body and "&gt;" in resp.body:
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send a marker containing < and > to a secure endpoint and "
                            "check the response body.")

    if check == "xss_evidence_collected":
        s = lab.xss
        if (s.reflected_seen and s.stored_seen and s.dom_seen
                and (s.secure_search_tested or s.secure_feedback_tested)):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Collect more evidence: reflected, stored, DOM, and a "
                            "secure-endpoint comparison.")

    # ── CSRF Fundamentals (YC-035.6). Each check reads either the last
    # request/response's structured 'X-Sim-CSRF-Kind' header (set
    # deterministically by WebApp's fixed training routes — see web.py)
    # or a flag/counter off WebLab.csrf (CsrfLabState) — never rendered
    # text, matching this file's established discipline.
    if check == "state_change_identified":
        if req is not None and req.path == "/transfer" and req.method == "POST":
            return _pass(obj_id, xp)
        return _fail(obj_id, "Send a POST request to /transfer first.")

    if check == "get_vs_post_identified":
        if (req is not None and req.path == "/transfer" and req.method == "GET"
                and resp is not None and resp.status_code == 404):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Try a GET request to /transfer (no -X flag) and observe "
                            "that no such route exists.")

    if check == "csrf_simulated":
        if lab.csrf.attack_simulated:
            return _pass(obj_id, xp)
        return _fail(obj_id, "Run the simulated attacker request against the "
                            "vulnerable /transfer endpoint (Origin: attacker.training).")

    if check == "csrf_token_identified":
        if lab.csrf.token_viewed:
            return _pass(obj_id, xp)
        return _fail(obj_id, "Open /secure-transfer while logged in to view your "
                            "training CSRF token.")

    if check == "missing_token_rejected":
        if resp is not None and resp.status_code == 403 \
                and resp.headers.get("X-Sim-CSRF-Kind") == "missing_token":
            return _pass(obj_id, xp)
        return _fail(obj_id, "POST to /secure-transfer without a csrf_token and "
                            "check for 403 Forbidden.")

    if check == "invalid_token_rejected":
        if resp is not None and resp.status_code == 403 \
                and resp.headers.get("X-Sim-CSRF-Kind") == "invalid_token":
            return _pass(obj_id, xp)
        return _fail(obj_id, "POST to /secure-transfer with an incorrect csrf_token "
                            "and check for 403 Forbidden.")

    if check == "valid_token_accepted":
        if resp is not None and resp.status_code == 200 \
                and resp.headers.get("X-Sim-CSRF-Kind") == "token_valid":
            return _pass(obj_id, xp)
        return _fail(obj_id, "POST to /secure-transfer with your correct training "
                            "csrf_token and check for 200 OK.")

    if check == "origin_rejected":
        if resp is not None and resp.status_code == 403 \
                and resp.headers.get("X-Sim-CSRF-Kind") == "origin_rejected":
            return _pass(obj_id, xp)
        return _fail(obj_id, "POST to /secure-transfer with an Origin header set to "
                            "https://attacker.training and check for 403 Forbidden.")

    if check == "samesite_inspected":
        if lab.csrf.samesite_inspected >= int(expected or 1):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Use 'samesite strict', 'samesite lax', and "
                            "'samesite none' to inspect all three policies.")

    if check == "csrf_evidence_collected":
        c = lab.csrf
        if (c.attack_simulated and c.token_viewed and c.missing_token_rejected
                and c.invalid_token_rejected and c.valid_token_accepted and c.origin_rejected):
            return _pass(obj_id, xp)
        return _fail(obj_id, "Collect more evidence: simulate the attack, view the "
                            "token, and test a missing token, an invalid token, a "
                            "valid token, and an unexpected Origin.")

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
