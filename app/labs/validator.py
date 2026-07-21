"""Validation engine — decides when an objective is satisfied.

Validators are pure functions over a ValidationContext. They are the SECOND
plugin axis of the Lab Engine:

    simulators  = how the simulated world responds to an action
    validators  = how we judge whether an objective was achieved

Keeping them separate is what stops lab-specific logic leaking into the
engine, the services or the routes.

=== EXTENSION POINT ===
Add a validator type without touching the engine:

    @register_validator("packet_flagged")
    def _packet_flagged(spec, ctx) -> bool:
        return ctx.event_value("flag", "asset_id") == spec.get("asset_id")

Any objective can then use validator_type="packet_flagged" with
validator_data={"asset_id": 42}. The engine discovers it by name — the
same objective row shape serves Terminal, Inspector, Packet Viewer,
Browser and Code Editor objectives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from app.labs.simulator_base import Action

# validator_type -> callable(spec: dict, ctx: ValidationContext) -> bool
VALIDATOR_REGISTRY: dict[str, Callable[..., bool]] = {}


def register_validator(name: str) -> Callable:
    """Decorator registering a validator function under ``name``."""

    def wrapper(fn: Callable[..., bool]) -> Callable[..., bool]:
        VALIDATOR_REGISTRY[name] = fn
        return fn

    return wrapper


@dataclass
class ValidationContext:
    """Everything a validator may inspect. Capability-agnostic by design."""

    action: Action                                  # what the user did
    output: str = ""                                # what the simulator returned
    state: dict[str, Any] = field(default_factory=dict)   # state AFTER the action
    events: list[dict[str, Any]] = field(default_factory=list)  # simulator signals

    # -- convenience accessors used by validators -----------------------
    @property
    def command(self) -> str:
        return self.action.command.strip()

    def event_value(self, event_type: str, key: str) -> Any:
        """First value of ``key`` among events of ``event_type``."""
        for event in self.events:
            if event.get("type") == event_type and key in event:
                return event[key]
        return None

    def state_value(self, path: str) -> Any:
        """Read a dotted path out of state, e.g. 'flags.created_projects'."""
        node: Any = self.state
        for part in (path or "").split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node


# ---------------------------------------------------------------------------
# Core validators (available to every simulator / capability)
# ---------------------------------------------------------------------------
@register_validator("exact_command")
def _exact_command(spec: dict, ctx: ValidationContext) -> bool:
    """The user typed exactly this command (whitespace-normalised).

    spec: {"command": "pwd", "case_sensitive": false}
    """
    expected = str(spec.get("command", "")).strip()
    actual = ctx.command
    if not spec.get("case_sensitive", False):
        expected, actual = expected.lower(), actual.lower()
    # Normalise internal whitespace so "cd   Documents" == "cd Documents".
    expected = " ".join(expected.split())
    actual = " ".join(actual.split())
    return bool(expected) and actual == expected


@register_validator("regex_command")
def _regex_command(spec: dict, ctx: ValidationContext) -> bool:
    """The command matches a regex.

    spec: {"pattern": "^mkdir\\s+projects$", "flags": "i"}
    """
    pattern = spec.get("pattern")
    if not pattern:
        return False
    flags = re.IGNORECASE if "i" in str(spec.get("flags", "")).lower() else 0
    try:
        return re.search(pattern, ctx.command, flags) is not None
    except re.error:
        return False


@register_validator("output_contains")
def _output_contains(spec: dict, ctx: ValidationContext) -> bool:
    """The simulator's output contains a substring (or matches a regex).

    spec: {"text": "note.txt"}  or  {"pattern": "flag\\{.*\\}"}
    """
    output = ctx.output or ""
    if "pattern" in spec:
        try:
            return re.search(spec["pattern"], output) is not None
        except re.error:
            return False
    text = str(spec.get("text", ""))
    if not text:
        return False
    if spec.get("case_sensitive", False):
        return text in output
    return text.lower() in output.lower()


@register_validator("state_flag")
def _state_flag(spec: dict, ctx: ValidationContext) -> bool:
    """A value in the simulated state matches an expectation.

    Capability-neutral: works for a terminal flag, an inspector cursor, a
    browser step — anything a simulator records in its state.

    spec: {"path": "flags.created_projects", "equals": true}
          {"path": "cwd", "equals": "/home/user/Documents"}
          {"path": "flags.visited", "min_length": 4}   # YC-026.0
          {"path": "directory.groups.domain-admins.members",
           "not_contains": "intern01"}                 # YC-031.0
    """
    path = spec.get("path")
    if not path:
        return False
    value = ctx.state_value(path)
    if "equals" in spec:
        return value == spec["equals"]
    if "min_length" in spec:
        try:
            return len(value) >= int(spec["min_length"])
        except TypeError:
            return False
    if "not_contains" in spec:
        # Remediation objectives: something must be ABSENT from a
        # collection (e.g. an intern removed from Domain Admins). A
        # missing path fails — absence of the whole structure is not
        # proof of remediation.
        if value is None:
            return False
        try:
            return spec["not_contains"] not in value
        except TypeError:
            return False
    return bool(value)  # presence/truthiness check


@register_validator("event_emitted")
def _event_emitted(spec: dict, ctx: ValidationContext) -> bool:
    """A simulator emitted a matching event.

    The generic hook for future capabilities (packet flagged, request
    intercepted, code executed…) with NO engine change.

    spec: {"event": "flag", "key": "asset_id", "equals": 42}
          {"event": "nmap", "key": "services", "contains": "http"}
          {"event": "code_run"}
    """
    event_type = spec.get("event")
    if not event_type:
        return False
    if "key" not in spec:
        return any(e.get("type") == event_type for e in ctx.events)
    value = ctx.event_value(event_type, spec["key"])
    if "equals" in spec:
        return value == spec["equals"]
    if "contains" in spec:
        # Works for lists (["http","https"]) and strings ("http")
        try:
            return spec["contains"] in value
        except TypeError:
            return False
    return value is not None


# ---------------------------------------------------------------------------
# Engine entry point
# ---------------------------------------------------------------------------
def validate(validator_type: str, validator_data: dict,
             ctx: ValidationContext) -> bool:
    """Run one validator. Unknown types return False (never raise)."""
    fn = VALIDATOR_REGISTRY.get(validator_type or "")
    if fn is None:
        return False
    try:
        return bool(fn(validator_data or {}, ctx))
    except Exception:  # noqa: BLE001 — a bad spec must never break a lab
        return False


def available_validators() -> list[str]:
    """All registered validator types (for admin/seed validation)."""
    return sorted(VALIDATOR_REGISTRY)
