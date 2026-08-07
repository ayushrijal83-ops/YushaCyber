"""Lab session — one isolated session per student per lab."""

from __future__ import annotations

import time
from typing import Any

from app.core.lab_engine.events import EventLog
from app.core.lab_engine.objective import ObjectiveResult, check
from app.core.lab_engine.progress import LabProgress
from app.core.lab_engine.types import LabDef, Workspace
from app.core.lab_engine.workspace import init_workspace


class LabSession:
    """One running lab session for a student."""

    def __init__(self, lab: LabDef, user_id: int,
                 workspace: Workspace | None = None) -> None:
        self.lab = lab
        self.user_id = user_id
        self.workspace = workspace or init_workspace(
            lab.lab_type, lab.workspace_config)
        self.progress = LabProgress(
            lab_slug=lab.slug, user_id=user_id,
            total_objectives=len([o for o in lab.objectives
                                  if not o.optional]),
            started=True)
        self.events = EventLog()
        self.started_at = time.time()
        self.events.emit("student_joined",
                         {"user_id": user_id, "lab": lab.slug})

    def submit(self, objective_id: str,
               submission: str = "",
               context: dict[str, Any] | None = None
               ) -> ObjectiveResult:
        """Submit an answer/command for an objective."""
        self.progress.add_attempt()
        for obj in self.lab.objectives:
            if obj.id == objective_id:
                result = check(obj, submission, context)
                if result.passed:
                    self.progress.complete(obj.id, result.xp_earned)
                    self.events.emit("objective_completed",
                                     {"objective_id": obj.id,
                                      "xp": result.xp_earned})
                    if self.progress.completed:
                        self.events.emit("lab_completed",
                                         {"xp_total": self.progress.xp_earned})
                return result
        return ObjectiveResult(objective_id=objective_id,
                               message="Objective not found.")

    def use_hint(self, objective_id: str = "") -> None:
        self.progress.use_hint()
        self.events.emit("hint_used",
                         {"objective_id": objective_id})

    def ask_ai(self, question: str) -> None:
        self.events.emit("ai_mentor_asked",
                         {"question": question[:200]})

    def current_objective(self):
        for obj in self.lab.objectives:
            if obj.id not in self.progress.completed_ids:
                return obj
        return None

    @property
    def elapsed_seconds(self) -> int:
        return int(time.time() - self.started_at)

    def to_dict(self) -> dict[str, Any]:
        cur = self.current_objective()
        return {
            "lab": self.lab.to_dict(),
            "user_id": self.user_id,
            "workspace": self.workspace.to_dict(),
            "progress": self.progress.to_dict(),
            "events": self.events.to_list(),
            "elapsed": self.elapsed_seconds,
            "current_objective": cur.to_dict() if cur else None,
        }

    def ai_context(self) -> dict[str, Any]:
        """Context dict for CyberMentor integration."""
        cur = self.current_objective()
        return {
            "lab_slug": self.lab.slug,
            "lab_title": self.lab.title,
            "lab_type": self.lab.lab_type,
            "difficulty": self.lab.difficulty,
            "current_objective": cur.to_dict() if cur else None,
            "completed_objectives": list(self.progress.completed_ids),
            "progress_pct": self.progress.pct,
            "hints_used": self.progress.hints_used,
            "attempts": self.progress.attempts,
            "elapsed": self.elapsed_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any],
                  lab: LabDef) -> LabSession:
        ws = Workspace.from_dict(data.get("workspace", {}))
        session = cls(lab, data.get("user_id", 0), ws)
        p = data.get("progress", {})
        session.progress.completed_ids = p.get("completed_ids", [])
        session.progress.xp_earned = p.get("xp_earned", 0)
        session.progress.hints_used = p.get("hints_used", 0)
        session.progress.attempts = p.get("attempts", 0)
        session.progress.completed = p.get("completed", False)
        session.events = EventLog.from_list(data.get("events", []))
        session.started_at = time.time() - data.get("elapsed", 0)
        return session
