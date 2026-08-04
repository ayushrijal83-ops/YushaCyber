"""Lab validator — checks commands, answers, and files against objectives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.lab_engine.objectives import Objective


@dataclass
class ValidationResult:
    passed: bool = False
    objective_id: str = ""
    message: str = ""
    xp_earned: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "objective_id": self.objective_id,
            "message": self.message,
            "xp_earned": self.xp_earned,
        }


def validate_command(objective: Objective, command: str,
                     output: str = "") -> ValidationResult:
    """Check if a command matches the objective's expected value."""
    expected = objective.expected.strip().lower()
    cmd = command.strip().lower()

    if not expected:
        return ValidationResult(passed=False,
                                objective_id=objective.id,
                                message="No validation rule defined.")

    # Exact match.
    if cmd == expected:
        return _pass(objective)

    # Partial match (expected is contained in command).
    if expected in cmd:
        return _pass(objective)

    # Output contains expected string.
    if output and expected in output.lower():
        return _pass(objective)

    return ValidationResult(
        passed=False, objective_id=objective.id,
        message="Not quite — try a different approach.")


def validate_answer(objective: Objective, answer: str) -> ValidationResult:
    """Check a text answer."""
    expected = objective.expected.strip().lower()
    given = answer.strip().lower()
    if given == expected:
        return _pass(objective)
    # Fuzzy: expected contained in answer.
    if expected in given or given in expected:
        return _pass(objective, "Close enough — accepted!")
    return ValidationResult(
        passed=False, objective_id=objective.id,
        message="That's not the answer we're looking for.")


def validate_file(objective: Objective, fs,
                  path: str = "") -> ValidationResult:
    """Check if a file exists or contains expected content."""
    target = path or objective.expected
    if fs.exists(target):
        return _pass(objective)
    return ValidationResult(
        passed=False, objective_id=objective.id,
        message=f"File '{target}' not found.")


def validate_objective(objective: Objective, command: str = "",
                       output: str = "", answer: str = "",
                       fs=None) -> ValidationResult:
    """Route to the right validator based on objective type."""
    if objective.validation_type == "answer":
        return validate_answer(objective, answer)
    if objective.validation_type == "file":
        return validate_file(objective, fs)
    return validate_command(objective, command, output)


def _pass(objective: Objective,
          message: str = "Objective completed!") -> ValidationResult:
    return ValidationResult(
        passed=True, objective_id=objective.id,
        message=message, xp_earned=objective.xp)
