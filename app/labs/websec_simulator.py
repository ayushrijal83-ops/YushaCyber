"""Web Security Simulator (YC-029.0).

A new simulator type (key=``web-security``) that plugs into the existing
lab engine. Students interact with simulated vulnerable web applications
via terminal commands: ``curl``, ``http``, ``inspect``, ``cookie``,
``session``, ``header``, ``submit``.

Reuses the Simulator base class, SimulatorRegistry, the validator/
objective engine, XP awards and achievement unlocks — unchanged.
"""

from __future__ import annotations

from typing import Any, Callable

from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_TERMINAL,
    Action,
    ActionResult,
    Simulator,
)
from app.labs.websec_engine import (
    HttpRequest, WebApp, get_scenario, list_scenarios, _safe_display,
)


@register_simulator
class WebSecuritySimulator(Simulator):
    """Interactive web security lab simulator."""

    key = "web-security"

    def capabilities(self) -> set[str]:
        return {CAP_TERMINAL}

    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        scenario_id = ""
        if content and isinstance(content, dict):
            scenario_id = content.get("scenario", "")
        if lab and hasattr(lab, "slug"):
            # Map lab slug to scenario
            scenario_id = scenario_id or _lab_to_scenario(lab.slug)
        return {
            "sim": self.key,
            "scenario": scenario_id,
            "cookies": {},
            "session": {},
            "authenticated": False,
            "history": [],
            "flags": {},
        }

    def prompt(self, state: dict[str, Any]) -> str:
        scenario_id = state.get("scenario", "http-basics")
        scenario = get_scenario(scenario_id)
        base = scenario.base_url if scenario else "http://app.local"
        return f"websec@{base.split('//')[1]}> "

    def welcome(self, state: dict[str, Any]) -> str:
        scenario_id = state.get("scenario", "http-basics")
        scenario = get_scenario(scenario_id)
        title = scenario.title if scenario else "Web Security Lab"
        desc = scenario.description if scenario else ""
        return (
            f"Web Security Lab: {title}\n"
            f"{desc}\n"
            f"\n"
            f"Commands: curl, http, inspect, cookie, session, header, submit, help\n"
            f"Type `help` for details. Everything is simulated — nothing is real."
        )

    def describe_ui(self) -> dict[str, Any]:
        return {"title": "Web Security Lab — simulated browser"}

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        scenario_id = state.get("scenario", "")
        scenario = get_scenario(scenario_id)
        return [
            {"label": "Scenario", "value": scenario.title if scenario else "—"},
            {"label": "Authenticated", "value": "Yes" if state.get("authenticated") else "No"},
            {"label": "Cookies", "value": str(len(state.get("cookies", {})))},
            {"label": "Requests Made", "value": str(len(state.get("history", [])))},
        ]

    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        state = dict(state) if state else self.bootstrap(None, {})
        if not state.get("sim"):
            state["sim"] = self.key
        if action.type == "command":
            return self._handle_command(state, action)
        return ActionResult(new_state=state)

    def _handle_command(self, state: dict[str, Any], action: Action) -> ActionResult:
        raw = action.command.strip()
        if not raw:
            return ActionResult(new_state=state)

        state.setdefault("flags", {})
        state["flags"]["commands_used"] = state["flags"].get("commands_used", 0) + 1

        parts = raw.split()
        cmd, args = parts[0].lower(), parts[1:]

        handler = self._dispatch_table().get(cmd)
        if handler is None:
            return ActionResult(
                output=f"{cmd}: command not found. Type `help` for available commands.",
                new_state=state)
        return handler(state, args)

    def _dispatch_table(self) -> dict[str, Callable]:
        return {
            "help":     self._cmd_help,
            "curl":     self._cmd_curl,
            "http":     self._cmd_http,
            "inspect":  self._cmd_inspect,
            "cookie":   self._cmd_cookie,
            "session":  self._cmd_session,
            "header":   self._cmd_header,
            "submit":   self._cmd_submit,
            "clear":    self._cmd_clear,
            "history":  self._cmd_history,
            "scenario": self._cmd_scenario,
        }

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _cmd_help(self, state, args):
        text = (
            "Web Security Lab Commands:\n"
            "  help                   show this list\n"
            "  curl <path>            send GET request (e.g. curl /)\n"
            "  curl -X POST <path>    send POST request\n"
            "  curl -d 'k=v' <path>   send POST with form data\n"
            "  http GET <path>        send a request with specified method\n"
            "  http POST <path> k=v   send POST with parameters\n"
            "  inspect                show last response details\n"
            "  inspect headers        show response headers\n"
            "  inspect cookies        show current cookies\n"
            "  cookie                 list all cookies\n"
            "  cookie set <k> <v>     set a cookie\n"
            "  cookie delete <k>      delete a cookie\n"
            "  session                show session info\n"
            "  header                 show security headers analysis\n"
            "  submit <param> <val>   submit a form parameter\n"
            "  history                show request history\n"
            "  scenario               show current scenario info\n"
            "  clear                  clear the terminal"
        )
        return ActionResult(output=text, new_state=state,
                            events=[{"type": "help_shown"}])

    def _cmd_curl(self, state, args):
        """Simulated curl: curl [-X METHOD] [-d 'data'] [-H 'header'] <path>"""
        method = "GET"
        data = ""
        headers = {}
        path = "/"
        i = 0
        while i < len(args):
            if args[i] == "-X" and i + 1 < len(args):
                method = args[i + 1].upper(); i += 2; continue
            elif args[i] == "-d" and i + 1 < len(args):
                data = args[i + 1].strip("'\""); method = "POST"; i += 2; continue
            elif args[i] == "-H" and i + 1 < len(args):
                h = args[i + 1].strip("'\"")
                if ":" in h:
                    k, v = h.split(":", 1)
                    headers[k.strip()] = v.strip()
                i += 2; continue
            else:
                path = args[i]; i += 1

        return self._send_request(state, method, path, data, headers)

    def _cmd_http(self, state, args):
        """Simulated httpie-style: http METHOD path key=value ..."""
        if not args:
            return ActionResult(output="usage: http METHOD <path> [key=value ...]",
                                new_state=state)
        method = args[0].upper() if args else "GET"
        path = args[1] if len(args) > 1 else "/"
        # Parse key=value pairs
        data_parts = []
        for a in args[2:]:
            if "=" in a:
                data_parts.append(a)
        data = "&".join(data_parts)
        if data and method == "GET":
            method = "POST"
        return self._send_request(state, method, path, data, {})

    def _cmd_submit(self, state, args):
        """Submit a parameter to the current scenario's vulnerable endpoint."""
        if len(args) < 2:
            return ActionResult(
                output="usage: submit <parameter> <value>\n"
                       "Example: submit username admin' OR 1=1--",
                new_state=state)
        param = args[0]
        value = " ".join(args[1:])
        scenario = get_scenario(state.get("scenario", ""))
        if not scenario:
            return ActionResult(output="No scenario loaded.", new_state=state)

        # Find the vulnerable endpoint
        vuln_endpoint = None
        for ep in scenario.endpoints:
            if ep.vulnerable_param:
                vuln_endpoint = ep; break
        if not vuln_endpoint:
            return ActionResult(output="No vulnerable endpoint in this scenario.",
                                new_state=state)

        data = f"{param}={value}"
        return self._send_request(state, vuln_endpoint.method, vuln_endpoint.path, data, {})

    def _send_request(self, state, method, path, data, extra_headers):
        """Core request sender — routes through the scenario's WebApp."""
        scenario = get_scenario(state.get("scenario", ""))
        if not scenario:
            return ActionResult(output="No scenario loaded.", new_state=state)

        app = WebApp(scenario)
        app.cookies = dict(state.get("cookies", {}))
        app.authenticated = state.get("authenticated", False)

        # Parse data into params
        params = {}
        if data:
            for pair in data.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v

        req = HttpRequest(
            method=method, path=path,
            headers={"User-Agent": "YushaCyber-WebSec/1.0", **extra_headers},
            cookies=dict(state.get("cookies", {})),
            params=params, body=data,
        )

        resp = app.handle_request(req)

        # Update state
        state["cookies"].update(resp.cookies)
        state["authenticated"] = app.authenticated
        state.setdefault("history", []).append({
            "request": req.to_dict(), "response": resp.to_dict(),
        })
        state["_last_response"] = resp.to_dict()

        # Format output
        lines = [
            f"HTTP/1.1 {resp.status_code} {resp.status_text}",
        ]
        for k, v in resp.headers.items():
            lines.append(f"{k}: {v}")
        if resp.cookies:
            for k, v in resp.cookies.items():
                lines.append(f"Set-Cookie: {k}={v}")
        lines.append("")
        lines.append(resp.body[:1500])

        # Track for objectives
        state.setdefault("flags", {})
        state["flags"].setdefault("methods_used", [])
        if method not in state["flags"]["methods_used"]:
            state["flags"]["methods_used"].append(method)
        state["flags"].setdefault("paths_visited", [])
        if path not in state["flags"]["paths_visited"]:
            state["flags"]["paths_visited"].append(path)
        if resp.vulnerable:
            state["flags"]["vuln_found"] = True
            state["flags"]["vuln_type"] = resp.vulnerability_type
            state["flags"].setdefault("vulns_found", [])
            if resp.vulnerability_type not in state["flags"]["vulns_found"]:
                state["flags"]["vulns_found"].append(resp.vulnerability_type)

        events = [{
            "type": "http_request",
            "method": method,
            "path": path,
            "status_code": resp.status_code,
            "vulnerable": resp.vulnerable,
            "vulnerability_type": resp.vulnerability_type,
            "has_params": bool(params),
        }]
        if resp.vulnerable:
            events.append({
                "type": "vuln_found",
                "vuln_type": resp.vulnerability_type,
                "param": next((ep.vulnerable_param for ep in scenario.endpoints
                              if ep.vulnerable_param), ""),
            })

        return ActionResult(
            output="\n".join(lines),
            new_state=state,
            events=events,
        )

    def _cmd_inspect(self, state, args):
        """Inspect the last HTTP response."""
        last = state.get("_last_response")
        if not last:
            return ActionResult(output="No response to inspect. Send a request first (try `curl /`).",
                                new_state=state)

        if args and args[0].lower() == "headers":
            lines = ["Response Headers:"]
            for k, v in last.get("headers", {}).items():
                lines.append(f"  {k}: {v}")
            return ActionResult(output="\n".join(lines), new_state=state,
                                events=[{"type": "inspect", "target": "headers"}])

        if args and args[0].lower() == "cookies":
            return self._cmd_cookie(state, [])

        lines = [
            f"Status: {last.get('status_code')} {last.get('status_text')}",
            "",
            "Headers:",
        ]
        for k, v in last.get("headers", {}).items():
            lines.append(f"  {k}: {v}")
        if last.get("cookies"):
            lines.append("")
            lines.append("Cookies:")
            for k, v in last["cookies"].items():
                lines.append(f"  {k} = {v}")
        lines.append("")
        lines.append("Body:")
        lines.append(last.get("body", "")[:1000])

        state.setdefault("flags", {})["inspected"] = True
        return ActionResult(
            output="\n".join(lines), new_state=state,
            events=[{"type": "inspect", "target": "full"}])

    def _cmd_cookie(self, state, args):
        """View, set, or delete cookies."""
        cookies = state.get("cookies", {})

        if args and args[0].lower() == "set" and len(args) >= 3:
            state.setdefault("cookies", {})[args[1]] = " ".join(args[2:])
            return ActionResult(
                output=f"Cookie set: {args[1]}={' '.join(args[2:])}",
                new_state=state,
                events=[{"type": "cookie_set", "name": args[1]}])

        if args and args[0].lower() == "delete" and len(args) >= 2:
            state.get("cookies", {}).pop(args[1], None)
            return ActionResult(
                output=f"Cookie deleted: {args[1]}",
                new_state=state,
                events=[{"type": "cookie_delete", "name": args[1]}])

        if not cookies:
            return ActionResult(output="No cookies set.", new_state=state,
                                events=[{"type": "cookie_view", "count": 0}])

        lines = ["Current Cookies:"]
        for k, v in cookies.items():
            secure = "🔒" if "secure" in v.lower() else "⚠️"
            httponly = "✅" if "httponly" in str(v).lower() else "❌"
            lines.append(f"  {k} = {v}")
            lines.append(f"    Secure: {secure}  HttpOnly: {httponly}")

        state.setdefault("flags", {})["cookies_inspected"] = True
        return ActionResult(
            output="\n".join(lines), new_state=state,
            events=[{"type": "cookie_view", "count": len(cookies),
                     "inspected": True}])

    def _cmd_session(self, state, args):
        """Show session information."""
        lines = [
            f"Authenticated: {'Yes' if state.get('authenticated') else 'No'}",
            f"Session cookies: {len(state.get('cookies', {}))}",
        ]
        scenario = get_scenario(state.get("scenario", ""))
        if scenario and scenario.session_config:
            lines.append("")
            lines.append("Session Configuration:")
            for k, v in scenario.session_config.items():
                flag = "✅" if v else "❌"
                lines.append(f"  {k}: {v} {flag}")
        state.setdefault("flags", {})["session_inspected"] = True
        return ActionResult(
            output="\n".join(lines), new_state=state,
            events=[{"type": "session_view", "authenticated": state.get("authenticated", False)}])

    def _cmd_header(self, state, args):
        """Analyse security headers of the last response."""
        last = state.get("_last_response")
        if not last:
            return ActionResult(output="No response to analyse. Send a request first.",
                                new_state=state)

        headers = last.get("headers", {})
        required = {
            "Strict-Transport-Security": "HSTS — forces HTTPS",
            "X-Content-Type-Options": "Prevents MIME sniffing",
            "X-Frame-Options": "Prevents clickjacking",
            "Content-Security-Policy": "Controls allowed resources",
            "Referrer-Policy": "Controls referrer leakage",
            "Permissions-Policy": "Controls browser features",
        }
        lines = ["Security Headers Analysis:"]
        present = 0
        for header, desc in required.items():
            if header in headers:
                lines.append(f"  ✅ {header}: {headers[header]}")
                present += 1
            else:
                lines.append(f"  ❌ {header}: MISSING — {desc}")
        lines.append("")
        lines.append(f"Score: {present}/{len(required)} security headers present")
        if present < len(required):
            lines.append("⚠️ Missing headers leave the application vulnerable.")

        state.setdefault("flags", {})["headers_analysed"] = True
        state["flags"]["security_score"] = present
        return ActionResult(
            output="\n".join(lines), new_state=state,
            events=[{"type": "header_analysis", "score": present,
                     "total": len(required), "analysed": True}])

    def _cmd_history(self, state, args):
        """Show request history."""
        hist = state.get("history", [])
        if not hist:
            return ActionResult(output="No requests made yet.", new_state=state)
        lines = [f"Request History ({len(hist)} requests):"]
        for i, entry in enumerate(hist[-10:], 1):
            req = entry.get("request", {})
            resp = entry.get("response", {})
            lines.append(
                f"  {i}. {req.get('method', '?')} {req.get('path', '?')} "
                f"→ {resp.get('status_code', '?')} {resp.get('status_text', '')}")
        return ActionResult(output="\n".join(lines), new_state=state)

    def _cmd_scenario(self, state, args):
        """Show current scenario details."""
        scenario = get_scenario(state.get("scenario", ""))
        if not scenario:
            return ActionResult(output="No scenario loaded.", new_state=state)
        lines = [
            f"Scenario: {scenario.title}",
            f"Base URL: {scenario.base_url}",
            f"Description: {scenario.description}",
            "",
            "Available Endpoints:",
        ]
        for ep in scenario.endpoints:
            params = f" ({', '.join(ep.params)})" if ep.params else ""
            auth = " [auth required]" if ep.requires_auth else ""
            lines.append(f"  {ep.method} {ep.path}{params}{auth}")
            lines.append(f"    {ep.description}")
        return ActionResult(
            output="\n".join(lines), new_state=state,
            events=[{"type": "scenario_viewed"}])

    def _cmd_clear(self, state, args):
        return ActionResult(output="", new_state=state, clear=True)


# ---------------------------------------------------------------------------
# Lab-to-scenario mapping
# ---------------------------------------------------------------------------
def _lab_to_scenario(slug: str) -> str:
    mapping = {
        "websec-http": "http-basics",
        "websec-sqli": "sqli-login",
        "websec-xss": "xss-reflected",
        "websec-csrf": "csrf-transfer",
        "websec-cookies": "session-security",
        "websec-headers": "security-headers",
        "websec-upload": "file-upload",
        "websec-auth": "auth-bypass",
    }
    return mapping.get(slug, "http-basics")
