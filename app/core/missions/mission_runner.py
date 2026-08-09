"""Mission runner — manages session + auto-validates on every command."""

from __future__ import annotations

import dataclasses
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.missions.mission_loader import get_mission
from app.core.missions.mission_validator import validate
from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.shell import Shell

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")


def _mask_session_id(sid: str | None) -> str | None:
    """Partial mask for the AI mentor's prompt context (YC-035.3) —
    never the full session id, even though it's always fictional training
    data. Mirrors how a real security-conscious tool would treat any
    session token."""
    if not sid:
        return None
    return sid[:4] + "****"


@dataclass
class MissionProgress:
    mission_id: str = ""
    user_id: int = 0
    completed_ids: list[str] = field(default_factory=list)
    total: int = 0
    xp_earned: int = 0
    hints_used: int = 0
    attempts: int = 0
    started_at: float = 0.0
    completed: bool = False
    hint_index: dict[str, int] = field(default_factory=dict)

    @property
    def pct(self) -> int:
        return int(len(self.completed_ids) / max(1, self.total) * 100)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pct"] = self.pct
        d["elapsed"] = int(time.time() - self.started_at) if self.started_at else 0
        return d


class MissionRunner:
    """One running mission session per student."""

    def __init__(self, mission_id: str, user_id: int) -> None:
        self.mission = get_mission(mission_id)
        if self.mission is None:
            raise ValueError(f"Mission '{mission_id}' not found.")
        # Build shell with mission-specific filesystem (+ optional
        # initial permission/ownership metadata for permissions missions).
        fs_tree = self.mission.get("filesystem")
        fs_perms = self.mission.get("permissions")
        fs = VirtualFS(tree=fs_tree, permissions=fs_perms)
        self.shell = Shell(fs=fs)
        self._attach_network(self.shell)
        self._attach_packet_lab(self.shell)
        self._attach_web_lab(self.shell)
        self.progress = MissionProgress(
            mission_id=mission_id, user_id=user_id,
            total=len(self.mission["objectives"]),
            started_at=time.time())
        self._last_output = ""

    def execute(self, command: str) -> dict[str, Any]:
        """Execute a command and auto-validate all pending objectives."""
        output = self.shell.execute(command)
        self._last_output = output
        self.progress.attempts += 1

        validations: list[dict[str, Any]] = []
        for obj in self.mission["objectives"]:
            if obj["id"] in self.progress.completed_ids:
                continue
            result = validate(obj, self.shell, command, output)
            if result.passed:
                self.progress.completed_ids.append(obj["id"])
                self.progress.xp_earned += result.xp
                validations.append(result.to_dict())

        if (len(self.progress.completed_ids) >=
                self.progress.total):
            self.progress.completed = True

        return {
            "output": output,
            "prompt": self.shell.prompt,
            "command": command,
            "validations": validations,
            "progress": self.progress.to_dict(),
            "completed": self.progress.completed,
            "network_status": self.network_status(),
            "packet_lab_status": self.packet_lab_status(),
            "web_lab_status": self.web_lab_status(),
        }

    def _attach_network(self, shell: Shell) -> None:
        """Attach the mission's declarative network config (if any) to a shell.

        Needed both on fresh construction and after Shell.from_dict()
        replaces the shell wholesale during resume. The static topology is
        always rebuilt fresh from the mission config; if a saved *mutation*
        snapshot is pending (student fixed/broke something before saving —
        see YC-034.6), it's replayed on top so resumed sessions keep it.
        """
        net_config = self.mission.get("network")
        if not net_config:
            return
        from app.core.terminal.network import build_network
        shell.network = build_network(net_config)
        pending = getattr(shell, "_pending_network_state", None)
        if pending:
            shell.network.apply_state(pending)
        shell._pending_network_state = None

    def network_status(self) -> dict[str, Any] | None:
        """Live network summary for the mission UI / AI mentor context."""
        net = self.shell.network
        if net is None:
            return None
        eth0 = next((i for i in net.student.interfaces if i.name != "lo"), None)
        return {
            "interface": eth0.name if eth0 else None,
            "interface_state": eth0.state if eth0 else "UNKNOWN",
            "interface_ip": f"{eth0.ip}/{eth0.cidr}" if eth0 else None,
            "default_gateway": net.default_gateway(),
            "dns_server": net.dns_server_ip,
        }

    def _attach_packet_lab(self, shell: Shell) -> None:
        """Attach the mission's declarative packet-capture list (if any).

        Mirrors _attach_network: captures are always rebuilt fresh and
        deterministically from the mission's capture names (see
        packets.py); if a saved session state is pending (which capture
        was open, which packet was selected, the last filter typed), it's
        replayed on top so a resumed session picks up where it left off.
        """
        capture_names = self.mission.get("packet_captures")
        if not capture_names:
            return
        from app.core.terminal.packets import build_packet_lab
        shell.packet_lab = build_packet_lab(capture_names)
        pending = getattr(shell, "_pending_packet_lab_state", None)
        if pending:
            shell.packet_lab.apply_state(pending)
        shell._pending_packet_lab_state = None

    def packet_lab_status(self) -> dict[str, Any] | None:
        """Live packet-lab summary for the mission UI / AI mentor context."""
        lab = self.shell.packet_lab
        if lab is None:
            return None
        return {
            "active_capture": lab.active.name if lab.active else None,
            "total_packets": len(lab.active.packets) if lab.active else 0,
            "selected_packet": lab.selected_packet,
            "last_filter": lab.last_filter,
        }

    def _attach_web_lab(self, shell: Shell) -> None:
        """Attach a simulated CyberShop web session (if this mission wants
        one). Mirrors _attach_network/_attach_packet_lab: the site and
        investigation transcript are always rebuilt fresh and
        deterministically; a saved session snapshot (cookie jar, request
        history, server-side login state) is replayed on top so a resumed
        session keeps its logged-in state.
        """
        web_config = self.mission.get("web_lab")
        if not web_config:
            return
        from app.core.terminal.web import build_web_lab
        # `web_lab` is either `True` (legacy — YC-035.0's default
        # scenario) or a scenario-name string (YC-035.1 needs its own
        # investigation transcript) — see web.py's _INVESTIGATION_BUILDERS.
        scenario = web_config if isinstance(web_config, str) else "login-flow"
        shell.web_lab = build_web_lab(scenario)
        pending = getattr(shell, "_pending_web_lab_state", None)
        if pending:
            shell.web_lab.apply_state(pending)
        shell._pending_web_lab_state = None

    def web_lab_status(self) -> dict[str, Any] | None:
        """Live web-session summary for the mission UI / AI mentor context.

        Carries full structured request/response/history data (YC-035.1)
        so the browser's HTTP Inspector panel can render Request/Response/
        Headers/Body/Cookies/History tabs without a second round trip —
        the same JSON already returned by execute()/to_dict()."""
        lab = self.shell.web_lab
        if lab is None:
            return None
        from app.core.terminal.web import DB_SCHEMA
        sid = lab.session.cookies.get("session_id")
        # "authenticated" (YC-035.3) is a *server-side* fact: the browser's
        # jar can hold a session_id the server no longer recognizes (after
        # logout or 'expire') — that mismatch is the whole point of the
        # Session State panel, so it's computed here rather than inferred
        # from cookie presence alone.
        authenticated = bool(sid and sid in lab.app.sessions)
        username = lab.app.sessions.get(sid) if sid else None
        req, resp = lab.session.last_request, lab.session.last_response
        return {
            "logged_in_as": username,
            "authenticated": authenticated,
            "session_present": sid is not None,
            "expired_count": lab.expired_count,
            "last_status": resp.status_code if resp else None,
            "last_path": req.path if req else None,
            "cookie_count": len(lab.session.cookies),
            "cookies": dict(lab.session.cookies),
            "last_request": dataclasses.asdict(req) if req else None,
            "last_response": dataclasses.asdict(resp) if resp else None,
            "history": [
                {"index": i + 1, "method": r.method, "path": r.path,
                 "status_code": s.status_code,
                 "request": dataclasses.asdict(r), "response": dataclasses.asdict(s)}
                for i, (r, s) in enumerate(lab.session.history[-20:])
            ],
            # Intercepting-proxy state (YC-035.2) — only meaningful for
            # missions that ever turn intercept on; every prior mission's
            # counters simply stay at their defaults, and the frontend
            # gates the Proxy Control panel on `pending`/counters being
            # non-default, not on this key's mere presence.
            "proxy": {
                "intercept_enabled": lab.proxy.intercept_enabled,
                "pending": dataclasses.asdict(lab.proxy.pending) if lab.proxy.pending else None,
                "intercepted_count": lab.proxy.intercepted_count,
                "forwarded_count": lab.proxy.forwarded_count,
                "dropped_count": lab.proxy.dropped_count,
                "blocked_count": lab.proxy.blocked_count,
                "repeater_request": dataclasses.asdict(lab.proxy.repeater_request)
                    if lab.proxy.repeater_request else None,
                "repeater_loaded_count": lab.proxy.repeater_loaded_count,
                "repeater_sent_count": lab.proxy.repeater_sent_count,
                "compared_count": lab.proxy.compared_count,
            },
            # SQL Injection Fundamentals state (YC-035.4) — only ever
            # meaningful for that mission; every other web-lab mission's
            # counters simply stay at their defaults, same as `proxy`
            # above for missions that never touch the proxy.
            "sqli": {
                "query_inspections": lab.sqli.query_inspections,
                "boolean_true_seen": lab.sqli.boolean_true_seen,
                "boolean_false_seen": lab.sqli.boolean_false_seen,
                "secure_search_tested": lab.sqli.secure_search_tested,
                "secure_login_tested": lab.sqli.secure_login_tested,
                "auth_bypass_triggered": lab.sqli.auth_bypass_triggered,
            },
            # Fixed, read-only training schema (YC-035.4) for the Database
            # Inspector panel — static data, not per-session state; carried
            # here so the frontend has a single source of truth instead of
            # duplicating DB_SCHEMA in the template.
            "db_schema": DB_SCHEMA,
            # XSS Fundamentals state (YC-035.5) — only ever meaningful for
            # that mission; every other web-lab mission's flags simply
            # stay at their defaults, same as `sqli`/`proxy` above.
            "xss": {
                "reflected_seen": lab.xss.reflected_seen,
                "stored_seen": lab.xss.stored_seen,
                "dom_seen": lab.xss.dom_seen,
                "secure_search_tested": lab.xss.secure_search_tested,
                "secure_feedback_tested": lab.xss.secure_feedback_tested,
            },
            # Stored training comments (YC-035.5) — small and structured,
            # for the Comments panel to render without a second command
            # round trip, mirroring `db_schema`'s "single source of truth"
            # rationale above.
            "comments": [dataclasses.asdict(c) for c in lab.app.comments],
        }

    def use_hint(self, objective_id: str) -> str:
        """Return the hint for an objective.

        Supports two shapes on an objective: a single `hint` string (every
        prior mission — unchanged, still works exactly as before), or a
        `hints` list of progressively more specific hints (YC-035.1 — "the
        answer" is never handed over on the first ask). Each *further*
        request for the same objective's hint advances one step deeper,
        capped at the last entry."""
        self.progress.hints_used += 1
        for obj in self.mission["objectives"]:
            if obj["id"] == objective_id:
                hints = obj.get("hints")
                if hints:
                    idx = self.progress.hint_index.get(objective_id, 0)
                    self.progress.hint_index[objective_id] = min(idx + 1, len(hints) - 1)
                    return hints[idx]
                return obj.get("hint", "No hint available.")
        return "Objective not found."

    def current_objective(self) -> dict[str, Any] | None:
        for obj in self.mission["objectives"]:
            if obj["id"] not in self.progress.completed_ids:
                return obj
        return None

    def _scanned_targets(self) -> list[str]:
        """IPv4 targets seen in nmap commands so far — derived from the
        existing shell history rather than a new tracking structure, so
        it works for any networking mission without per-mission wiring."""
        targets: list[str] = []
        for line in self.shell.history:
            if not line.strip().lower().startswith("nmap"):
                continue
            for m in _IPV4_RE.findall(line):
                if m not in targets:
                    targets.append(m)
        return targets

    def ai_context(self) -> dict[str, Any]:
        cur = self.current_objective()
        ctx: dict[str, Any] = {
            "mission": self.mission["title"],
            "mission_id": self.progress.mission_id,
            "current_objective": cur.get("title") if cur else "All complete",
            "current_description": cur.get("description") if cur else "",
            "completed": list(self.progress.completed_ids),
            "progress_pct": self.progress.pct,
            "hints_used": self.progress.hints_used,
            "last_command": self.shell.history[-1] if self.shell.history else "",
            "last_output": self._last_output,
            "cwd": self.shell.fs.cwd,
        }
        net_status = self.network_status()
        if net_status is not None:
            ctx["network"] = net_status
            ctx["scanned_targets"] = self._scanned_targets()
        pkt_status = self.packet_lab_status()
        if pkt_status is not None:
            ctx["packet_lab"] = pkt_status
        web_status = self.web_lab_status()
        if web_status is not None:
            # A trimmed view for the AI mentor prompt (YC-035.1 wants the
            # mentor aware of the current endpoint, last request/response,
            # headers, cookies, and recent history) — the *full* payload in
            # web_lab_status() is sized for the browser's HTTP Inspector
            # panel, not for repeating entire raw bodies on every mentor
            # turn, so only headers (small, useful) and a short history
            # summary (method/path/status, not full objects) are included.
            req, resp = web_status["last_request"], web_status["last_response"]
            ctx["web"] = {
                "logged_in_as": web_status["logged_in_as"],
                "last_path": web_status["last_path"],
                "last_status": web_status["last_status"],
                "last_request_headers": req["headers"] if req else {},
                "last_response_headers": resp["headers"] if resp else {},
                "cookies": web_status["cookies"],
                "recent_history": [
                    f"{h['method']} {h['path']} -> {h['status_code']}"
                    for h in web_status["history"][-5:]
                ],
                # Authentication/session state (YC-035.3) — security-filtered:
                # the session id itself is masked (a handful of leading
                # characters + '****'), never the full value, even though
                # it's fictional training data, so CyberMentor's prompt
                # never carries a copy-pasteable "secret" out of habit.
                "authentication_state": ("authenticated" if web_status["authenticated"]
                                        else "unauthenticated"),
                "session_id_present": web_status["session_present"],
                "session_active": web_status["authenticated"],
                "session_expired": (web_status["session_present"]
                                    and not web_status["authenticated"]),
                "session_id_masked": _mask_session_id(web_status["cookies"].get("session_id")),
                "last_authentication_status": web_status["last_status"],
            }
            # Proxy summary (YC-035.2) — small and structured, not the
            # full pending/repeater request objects, matching the same
            # "small, useful" sizing rationale as the rest of this dict.
            proxy = web_status["proxy"]
            pending_req = proxy["pending"]
            ctx["web"]["proxy"] = {
                "intercept_enabled": proxy["intercept_enabled"],
                "pending_request": (f"{pending_req['method']} {pending_req['path']}"
                                    if pending_req else None),
                "repeater_loaded": proxy["repeater_request"] is not None,
                "intercepted_count": proxy["intercepted_count"],
                "forwarded_count": proxy["forwarded_count"],
                "dropped_count": proxy["dropped_count"],
            }
            # SQL Injection Fundamentals summary (YC-035.4) — small and
            # structured, so CyberMentor can explain *why* a response
            # changed (which training condition was sent, whether the
            # secure endpoint has been compared yet) without repeating
            # full request/response bodies on every turn.
            sqli = web_status["sqli"]
            last_kind = (web_status["last_response"]["headers"].get("X-Sim-Query-Kind")
                        if web_status["last_response"] else None)
            ctx["web"]["injection"] = {
                "last_query_kind": last_kind,
                "query_inspections": sqli["query_inspections"],
                "boolean_true_observed": sqli["boolean_true_seen"],
                "boolean_false_observed": sqli["boolean_false_seen"],
                "secure_search_tested": sqli["secure_search_tested"],
                "secure_login_tested": sqli["secure_login_tested"],
                "auth_bypass_triggered": sqli["auth_bypass_triggered"],
            }
            # XSS Fundamentals summary (YC-035.5) — small and structured,
            # so CyberMentor can explain *why* something is reflected vs.
            # stored vs. DOM-based from actual mission state, without
            # repeating full response bodies (which may contain the
            # simulated-event panel text) on every turn.
            xss = web_status["xss"]
            last_xss_kind = (web_status["last_response"]["headers"].get("X-Sim-XSS-Kind")
                             if web_status["last_response"] else None)
            last_xss_context = (web_status["last_response"]["headers"].get("X-Sim-XSS-Context")
                                if web_status["last_response"] else None)
            ctx["web"]["xss"] = {
                "last_xss_kind": last_xss_kind,
                "last_xss_context": last_xss_context,
                "reflected_seen": xss["reflected_seen"],
                "stored_seen": xss["stored_seen"],
                "dom_seen": xss["dom_seen"],
                "secure_search_tested": xss["secure_search_tested"],
                "secure_feedback_tested": xss["secure_feedback_tested"],
                "stored_comment_count": len(web_status["comments"]),
            }
        return ctx

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission": {
                "id": self.mission["id"],
                "title": self.mission["title"],
                "description": self.mission["description"],
                "difficulty": self.mission["difficulty"],
                "xp_total": self.mission["xp_total"],
                "next_mission": self.mission.get("next_mission"),
                "objectives": [{
                    "id": o["id"], "title": o["title"],
                    "description": o["description"],
                    "xp": o["xp"],
                    "completed": o["id"] in self.progress.completed_ids,
                } for o in self.mission["objectives"]],
            },
            "progress": self.progress.to_dict(),
            "prompt": self.shell.prompt,
            "current_objective": self.current_objective(),
            "network_status": self.network_status(),
            "packet_lab_status": self.packet_lab_status(),
            "web_lab_status": self.web_lab_status(),
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> MissionRunner:
        mid = state["progress"]["mission_id"]
        uid = state["progress"]["user_id"]
        runner = cls(mid, uid)
        p = state["progress"]
        runner.progress.completed_ids = p.get("completed_ids", [])
        runner.progress.xp_earned = p.get("xp_earned", 0)
        runner.progress.hints_used = p.get("hints_used", 0)
        runner.progress.attempts = p.get("attempts", 0)
        runner.progress.completed = p.get("completed", False)
        runner.progress.hint_index = p.get("hint_index", {})
        runner.progress.started_at = (
            time.time() - p.get("elapsed", 0))
        if "shell" in state:
            runner.shell = Shell.from_dict(state["shell"])
            runner._attach_network(runner.shell)
            runner._attach_packet_lab(runner.shell)
            runner._attach_web_lab(runner.shell)
        return runner

    def save_state(self) -> dict[str, Any]:
        return {
            "progress": self.progress.to_dict(),
            "shell": self.shell.to_dict(),
        }
