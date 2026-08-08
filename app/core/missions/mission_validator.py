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


def _pass(obj_id: str, xp: int) -> ValidationResult:
    return ValidationResult(passed=True, objective_id=obj_id,
                            message="✓ Objective Complete!", xp=xp)


def _fail(obj_id: str, msg: str) -> ValidationResult:
    return ValidationResult(passed=False, objective_id=obj_id,
                            message=msg)
