"""Session manager — owns the lifecycle of a user's simulated lab session.

Engine-level and completely simulator-agnostic: it starts, loads, persists
and resets sessions without knowing whether the lab is a Linux terminal, a
Wireshark capture or a Burp proxy. It resolves the simulator through the
registry and delegates all world-behaviour to it.

Responsibilities:
  * create/resume a UserLabSession (one per user per lab)
  * load a lab's seeded content and hand it to the simulator's bootstrap()
  * persist opaque simulator state (JSON) between requests
  * reset a session's state without destroying objective/XP history

NOT its job: judging objectives, awarding XP (that's lab_services), or
interpreting state internals (that's the simulator).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.extensions import db
from app.labs.models import Lab, LabFileSystemNode, UserLabSession
from app.labs.registry import SimulatorRegistry
from app.labs.simulator_base import Simulator, SimulatorError


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Content loading
#
# EXTENSION POINT: when a future lab type needs a different kind of seeded
# content (packets, HTTP transactions, log lines), add a loader here keyed by
# the content it owns. The simulator receives whatever this returns and
# interprets it — the engine never inspects the contents.
# ---------------------------------------------------------------------------
def load_lab_content(lab: Lab) -> dict[str, Any]:
    """Gather a lab's seeded content for its simulator's bootstrap()."""
    nodes = (
        LabFileSystemNode.query
        .filter_by(lab_id=lab.id)
        .order_by(LabFileSystemNode.path)
        .all()
    )
    return {
        "filesystem": [
            {
                "path": n.path,
                "node_type": n.node_type,
                "content": n.content,
                "permissions": n.permissions,
                "owner": n.owner,
            }
            for n in nodes
        ],
        # Future: "packets": [...], "http_txns": [...], "logs": [...]
    }


def get_simulator(lab: Lab) -> Simulator:
    """Resolve the simulator plugin for a lab (raises if unregistered)."""
    return SimulatorRegistry.require(lab.simulator_key)


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------
def get_session(user, lab: Lab) -> Optional[UserLabSession]:
    """The user's existing session for a lab, or None."""
    if user is None or lab is None:
        return None
    return UserLabSession.query.filter_by(
        user_id=user.id, lab_id=lab.id
    ).first()


def start_session(user, lab: Lab) -> UserLabSession:
    """Create a session (bootstrapping fresh state) or resume the existing one."""
    session = get_session(user, lab)
    if session is not None:
        return session

    simulator = get_simulator(lab)
    state = simulator.bootstrap(lab, load_lab_content(lab))

    session = UserLabSession(
        user_id=user.id, lab_id=lab.id, status="active",
        last_activity_at=_utcnow(),
    )
    session.set_state(state)
    db.session.add(session)
    db.session.commit()
    return session


def reset_session(user, lab: Lab) -> UserLabSession:
    """Re-bootstrap a session's simulated state.

    Objective and XP history are deliberately PRESERVED (they live in
    UserObjectiveProgress / UserLabProgress), so resetting cannot be used to
    farm XP — matching the award-once rule used by quizzes and CTF.
    """
    session = start_session(user, lab)
    simulator = get_simulator(lab)
    session.set_state(simulator.bootstrap(lab, load_lab_content(lab)))
    session.status = "active"
    session.last_activity_at = _utcnow()
    db.session.commit()
    return session


def save_state(session: UserLabSession, state: dict[str, Any]) -> None:
    """Persist simulator state after an action."""
    session.set_state(state)
    session.last_activity_at = _utcnow()
    db.session.commit()


def load_state(session: UserLabSession, simulator: Simulator,
               lab: Lab) -> dict[str, Any]:
    """Read a session's state, re-bootstrapping if it's missing or foreign.

    Guards against a state written by a different simulator (e.g. a lab whose
    simulator_key was changed) — the envelope's ``sim`` key makes that
    detectable rather than silently corrupting a session.
    """
    state = session.get_state()
    if not state or state.get("sim") != simulator.key:
        state = simulator.bootstrap(lab, load_lab_content(lab))
        save_state(session, state)
    return state
