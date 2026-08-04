"""Lab engine services — the public API."""

from __future__ import annotations

from typing import Any

from app.lab_engine import state
from app.lab_engine.models import get_lab, list_labs
from app.lab_engine.simulator import LabSimulator

# Active sessions: {(user_id, slug): LabSimulator}
_sessions: dict[tuple[int, str], LabSimulator] = {}


def start_lab(user_id: int, slug: str) -> dict[str, Any]:
    """Start or resume a lab session."""
    lab = get_lab(slug)
    if lab is None:
        return {"error": f"Lab '{slug}' not found."}

    # Resume from saved state.
    saved = state.load(user_id, slug)
    if saved:
        sim = LabSimulator.from_dict(saved, lab)
    else:
        sim = LabSimulator(lab, user_id)

    _sessions[(user_id, slug)] = sim
    return sim.to_dict()


def execute_command(user_id: int, slug: str,
                    command: str) -> dict[str, Any]:
    """Execute a terminal command in the lab."""
    sim = _sessions.get((user_id, slug))
    if sim is None:
        return {"error": "No active session. Start the lab first."}
    result = sim.execute(command)
    # Auto-save.
    state.save(user_id, slug, sim.to_dict())
    return result


def submit_answer(user_id: int, slug: str,
                  objective_id: str,
                  answer: str) -> dict[str, Any]:
    """Submit a text answer for an objective."""
    sim = _sessions.get((user_id, slug))
    if sim is None:
        return {"error": "No active session."}
    result = sim.submit_answer(objective_id, answer)
    state.save(user_id, slug, sim.to_dict())
    return result


def get_session(user_id: int, slug: str) -> dict[str, Any] | None:
    """Get current session state."""
    sim = _sessions.get((user_id, slug))
    return sim.to_dict() if sim else None


def reset_lab(user_id: int, slug: str) -> dict[str, Any]:
    """Reset a lab to its initial state."""
    _sessions.pop((user_id, slug), None)
    state.reset(user_id, slug)
    return start_lab(user_id, slug)


def available_labs() -> list[dict[str, Any]]:
    return list_labs()
