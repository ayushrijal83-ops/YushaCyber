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


def validate(objective: dict[str, Any], shell: Shell,
             command: str = "", output: str = "") -> ValidationResult:
    """Validate an objective against the current shell state."""
    v = objective.get("validate", {})
    v_type = v.get("type", "command")
    expected = v.get("match", "").strip()
    obj_id = objective.get("id", "")
    xp = objective.get("xp", 0)

    if v_type == "command":
        cmd_lower = command.strip().lower()
        exp_lower = expected.lower()
        if cmd_lower == exp_lower or exp_lower in cmd_lower:
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
        content = shell.fs.read(v.get("path", "")) or ""
        if expected.lower() in content.lower():
            return _pass(obj_id, xp)
        return _fail(obj_id, "File doesn't contain the expected content.")

    if v_type == "output_contains":
        if expected.lower() in output.lower():
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

    return _fail(obj_id, "Unknown validation type.")


def _pass(obj_id: str, xp: int) -> ValidationResult:
    return ValidationResult(passed=True, objective_id=obj_id,
                            message="✓ Objective Complete!", xp=xp)


def _fail(obj_id: str, msg: str) -> ValidationResult:
    return ValidationResult(passed=False, objective_id=obj_id,
                            message=msg)
