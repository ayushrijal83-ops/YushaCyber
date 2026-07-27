"""Shared types for the Scenario Engine."""

from __future__ import annotations

from enum import Enum
from typing import Any


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    EXPERT = "Expert"


class Grade(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    PASS = "Pass"
    NEEDS_IMPROVEMENT = "Needs Improvement"
    FAIL = "Fail"


class ObjectiveType(str, Enum):
    """Every supported objective type. New modules extend this enum."""
    VISIT_PAGE = "visit_page"
    INSPECT_EVIDENCE = "inspect_evidence"
    EXECUTE_COMMAND = "execute_command"
    ANSWER_QUESTION = "answer_question"
    IDENTIFY_IOC = "identify_ioc"
    COMPLETE_TIMELINE = "complete_timeline"
    WRITE_REPORT = "write_report"
    UPLOAD_FINDING = "upload_finding"
    CUSTOM = "custom"


class ReportType(str, Enum):
    INCIDENT = "incident"
    FORENSICS = "forensics"
    HUNT = "hunt"
    ASSESSMENT = "assessment"
    EXECUTIVE = "executive"
    CUSTOM = "custom"


class ValidationRule:
    """One validation rule — wraps a validator type + data dict."""

    __slots__ = ("validator_type", "data")

    def __init__(self, validator_type: str,
                 data: dict[str, Any] | None = None):
        self.validator_type = validator_type
        self.data = data or {}

    def to_dict(self) -> dict[str, Any]:
        return {"validator_type": self.validator_type,
                "data": self.data}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ValidationRule":
        return cls(d.get("validator_type", ""),
                   d.get("data") or {})

    # ---- Convenience constructors ----
    @classmethod
    def exact_match(cls, path: str,
                    expected: Any) -> "ValidationRule":
        return cls("exact_match",
                   {"path": path, "expected": expected})

    @classmethod
    def multi_step(cls, events: list[str]) -> "ValidationRule":
        return cls("multi_step", {"events": events})

    @classmethod
    def ordered_steps(cls, events: list[str]) -> "ValidationRule":
        return cls("ordered_tasks", {"events": events})

    @classmethod
    def score_threshold(cls, path: str,
                        minimum: float) -> "ValidationRule":
        return cls("score_threshold", {"path": path, "min": minimum})

    @classmethod
    def event_emitted(cls, event: str) -> "ValidationRule":
        return cls("event_emitted", {"event": event})

    @classmethod
    def state_flag(cls, path: str,
                   equals: Any) -> "ValidationRule":
        return cls("state_flag", {"path": path, "equals": equals})

    @classmethod
    def custom(cls, function: str,
               **kwargs: Any) -> "ValidationRule":
        return cls("custom_hook",
                   {"function": function, **kwargs})
