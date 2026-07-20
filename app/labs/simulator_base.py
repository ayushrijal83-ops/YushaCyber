"""Simulator base contract — the core extension point of the Lab Engine.

Every simulator (Linux today; Nmap, Wireshark, Burp, SOC, Active Directory,
Python Security tomorrow) implements this one interface. The engine, the
service layer and the routes depend ONLY on this abstraction — never on a
concrete simulator (dependency inversion). Adding a lab type must therefore
never require a change to the engine, services, routes or models.

=== SAFETY (non-negotiable) ===
A simulator is a PURE FUNCTION of (state, action) -> ActionResult.
It NEVER executes anything: no subprocess, no os.system, no eval/exec, no
shell, no filesystem access. Every response is computed from seeded data and
in-memory simulated state.

=== EXTENSION POINT ===
To add a lab type:
    1. Subclass Simulator in app/labs/simulators/<key>.py
    2. Set `key` and implement bootstrap() / handle() / capabilities()
    3. Register it (see registry.py)
    4. Seed a Lab row with simulator_key=<key> plus its content
No other file changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

# Interaction capabilities a simulator may expose. The frontend renders
# whichever the simulator declares; the engine stays agnostic.
CAP_TERMINAL = "terminal"       # raw command input (Linux, Bash, Nmap, AD…)
CAP_INSPECTOR = "inspector"     # select/flag artifacts (Wireshark, Burp, SOC…)
CAP_BROWSER = "browser"         # simulated web app (XSS, SQLi…)
CAP_EDITOR = "editor"           # code editor (Python Security…)


@dataclass
class Action:
    """A single user interaction, normalised for every capability.

    ``type`` tells the simulator which kind of interaction this is:
      - "command"  -> payload {"command": "<raw text>"}      (terminal)
      - "select"   -> payload {"asset_id": ...}              (inspector)
      - "flag"     -> payload {"asset_id": ...}              (inspector)
      - "submit"   -> payload {"objective_id":…, "value":…}  (any)
    Future capabilities add new ``type`` values WITHOUT engine changes.
    """

    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def command(self) -> str:
        """Convenience accessor for terminal actions."""
        return str(self.payload.get("command", "") or "")


@dataclass
class ActionResult:
    """What a simulator returns. Plain data — no ORM, no side effects.

    output      : text/structured output to display to the user
    new_state   : the full replacement session state (JSON-serialisable)
    events      : signals the objective engine may validate against, e.g.
                  [{"type": "flag_set", "key": "created_projects"}]
    clear       : if True, the UI should clear its transcript (e.g. `clear`)
    """

    output: str = ""
    new_state: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    clear: bool = False


class Simulator(ABC):
    """Abstract base every simulator plugin implements."""

    #: Matches Lab.simulator_key in the database. Unique per simulator.
    key: str = ""

    # ------------------------------------------------------------------
    # Required interface
    # ------------------------------------------------------------------
    @abstractmethod
    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        """Build the initial session state for a lab.

        ``content`` is the lab's seeded content, loaded by the engine and
        handed over untouched (e.g. filesystem nodes for terminal labs,
        packets for a future Wireshark lab). The simulator decides how to
        interpret it. Returns a JSON-serialisable state dict.
        """

    @abstractmethod
    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        """Process one action against the state and return the result.

        MUST be pure: no I/O, no DB, no execution. Return a NEW state rather
        than mutating shared structures.
        """

    @abstractmethod
    def capabilities(self) -> set[str]:
        """Which interaction modes this simulator supports (CAP_* constants)."""

    # ------------------------------------------------------------------
    # Optional hooks (sane defaults; override when useful)
    # ------------------------------------------------------------------
    def prompt(self, state: dict[str, Any]) -> str:
        """The prompt string shown to the user (terminal simulators)."""
        return state.get("prompt", "$ ")

    def describe_ui(self) -> dict[str, Any]:
        """Hints for the frontend about how to render this simulator."""
        return {"capabilities": sorted(self.capabilities())}

    def welcome(self, state: dict[str, Any]) -> str:
        """Optional banner shown when a session starts."""
        return ""

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        """Optional key/value status items the workspace sidebar renders.

        Simulator-agnostic: each item is {"label": str, "value": str} plus an
        optional "state" ("ok"/"warn"/"err") for colouring. Default is no
        panel, so existing simulators are unaffected. A networking simulator
        may show host/IP/gateway; a future SOC simulator could show
        alert-queue depth — the engine never interprets the contents.
        """
        return []

    # ------------------------------------------------------------------
    # State envelope helpers — the ONLY parts of state the engine reads.
    # ------------------------------------------------------------------
    def new_state_envelope(self, **extra: Any) -> dict[str, Any]:
        """Create a state dict carrying the standard engine envelope.

        ``sim`` lets the engine confirm which simulator owns a state;
        ``version`` lets a simulator migrate its own state shape later
        without breaking in-flight sessions.
        """
        state = {"sim": self.key, "version": 1}
        state.update(extra)
        return state


class SimulatorError(Exception):
    """Raised for engine-level simulator problems (unknown key, bad state)."""
