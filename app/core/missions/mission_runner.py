"""Mission runner — manages session + auto-validates on every command."""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.missions.mission_loader import get_mission
from app.core.missions.mission_validator import validate
from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.shell import Shell

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")


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
        if not self.mission.get("web_lab"):
            return
        from app.core.terminal.web import build_web_lab
        shell.web_lab = build_web_lab()
        pending = getattr(shell, "_pending_web_lab_state", None)
        if pending:
            shell.web_lab.apply_state(pending)
        shell._pending_web_lab_state = None

    def web_lab_status(self) -> dict[str, Any] | None:
        """Live web-session summary for the mission UI / AI mentor context."""
        lab = self.shell.web_lab
        if lab is None:
            return None
        sid = lab.session.cookies.get("session_id")
        username = lab.app.sessions.get(sid) if sid else None
        resp = lab.session.last_response
        return {
            "logged_in_as": username,
            "last_status": resp.status_code if resp else None,
            "last_path": lab.session.last_request.path if lab.session.last_request else None,
            "cookie_count": len(lab.session.cookies),
        }

    def use_hint(self, objective_id: str) -> str:
        """Return the hint for an objective."""
        self.progress.hints_used += 1
        for obj in self.mission["objectives"]:
            if obj["id"] == objective_id:
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
            ctx["web"] = web_status
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
