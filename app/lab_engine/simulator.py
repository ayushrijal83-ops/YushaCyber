"""Lab simulator — orchestrates the full interactive lab session."""

from __future__ import annotations

from typing import Any

from app.lab_engine.filesystem import VirtualFS
from app.lab_engine.objectives import LabDefinition, Objective
from app.lab_engine.progress import LabProgress
from app.lab_engine.terminal import Terminal
from app.lab_engine.validator import validate_objective


class LabSimulator:
    """One running lab session for a student."""

    def __init__(self, lab: LabDefinition, user_id: int = 0) -> None:
        self.lab = lab
        self.user_id = user_id
        fs_tree = lab.filesystem
        self.terminal = Terminal(
            fs=VirtualFS(tree=fs_tree) if fs_tree else VirtualFS(),
            mode=lab.mode)
        self.progress = LabProgress(
            lab_slug=lab.slug, user_id=user_id,
            total_objectives=len(lab.objectives),
            started=True)

    def execute(self, command: str) -> dict[str, Any]:
        """Execute a command and auto-validate objectives."""
        output = self.terminal.execute(command)
        # Check all incomplete objectives.
        validations: list[dict[str, Any]] = []
        for obj in self.lab.objectives:
            if obj.id in self.progress.completed_objectives:
                continue
            result = validate_objective(
                obj, command=command, output=output,
                fs=self.terminal.fs)
            if result.passed:
                self.progress.complete_objective(
                    obj.id, result.xp_earned)
                obj.completed = True
                validations.append(result.to_dict())
        return {
            "output": output,
            "prompt": self.terminal.prompt,
            "validations": validations,
            "progress": self.progress.to_dict(),
        }

    def submit_answer(self, objective_id: str,
                      answer: str) -> dict[str, Any]:
        """Submit a text answer for an objective."""
        for obj in self.lab.objectives:
            if obj.id == objective_id:
                result = validate_objective(
                    obj, answer=answer, fs=self.terminal.fs)
                if result.passed:
                    self.progress.complete_objective(
                        obj.id, result.xp_earned)
                    obj.completed = True
                return result.to_dict()
        return {"passed": False, "message": "Objective not found."}

    def current_objective(self) -> Objective | None:
        for obj in self.lab.objectives:
            if obj.id not in self.progress.completed_objectives:
                return obj
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "lab": self.lab.to_dict(),
            "terminal": self.terminal.to_dict(),
            "progress": self.progress.to_dict(),
            "current_objective": (self.current_objective().to_dict()
                                  if self.current_objective() else None),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any],
                  lab: LabDefinition) -> LabSimulator:
        sim = cls(lab, data.get("progress", {}).get("user_id", 0))
        sim.terminal = Terminal.from_dict(data.get("terminal", {}))
        p = data.get("progress", {})
        sim.progress.completed_objectives = p.get(
            "completed_objectives", [])
        sim.progress.xp_earned = p.get("xp_earned", 0)
        sim.progress.completed = p.get("completed", False)
        return sim
