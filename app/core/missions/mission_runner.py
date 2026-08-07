"""Mission runner — manages session + auto-validates on every command."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.missions.mission_loader import get_mission
from app.core.missions.mission_validator import validate
from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.shell import Shell


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
        # Build shell with mission-specific filesystem.
        fs_tree = self.mission.get("filesystem")
        fs = VirtualFS(tree=fs_tree) if fs_tree else VirtualFS()
        self.shell = Shell(fs=fs)
        self.progress = MissionProgress(
            mission_id=mission_id, user_id=user_id,
            total=len(self.mission["objectives"]),
            started_at=time.time())

    def execute(self, command: str) -> dict[str, Any]:
        """Execute a command and auto-validate all pending objectives."""
        output = self.shell.execute(command)
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

    def ai_context(self) -> dict[str, Any]:
        cur = self.current_objective()
        return {
            "mission": self.mission["title"],
            "mission_id": self.progress.mission_id,
            "current_objective": cur.get("title") if cur else "All complete",
            "current_description": cur.get("description") if cur else "",
            "completed": list(self.progress.completed_ids),
            "progress_pct": self.progress.pct,
            "hints_used": self.progress.hints_used,
            "last_command": self.shell.history[-1] if self.shell.history else "",
            "cwd": self.shell.fs.cwd,
        }

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
        return runner

    def save_state(self) -> dict[str, Any]:
        return {
            "progress": self.progress.to_dict(),
            "shell": self.shell.to_dict(),
        }
