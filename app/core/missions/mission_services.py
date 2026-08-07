"""Mission services — public API with state persistence."""

from __future__ import annotations

from typing import Any

from app.core.missions.mission_loader import get_mission, list_missions
from app.core.missions.mission_runner import MissionRunner

# State store: {(user_id, mission_id): saved_state}
_state: dict[tuple[int, str], dict[str, Any]] = {}
# Active runners.
_runners: dict[tuple[int, str], MissionRunner] = {}


def start_mission(user_id: int,
                  mission_id: str) -> dict[str, Any]:
    """Start or resume a mission."""
    key = (user_id, mission_id)
    # Resume from saved state.
    if key in _state:
        try:
            runner = MissionRunner.from_state(_state[key])
            _runners[key] = runner
            return runner.to_dict()
        except (KeyError, ValueError, RuntimeError):
            pass
    # Fresh start.
    mission = get_mission(mission_id)
    if mission is None:
        return {"error": f"Mission '{mission_id}' not found."}
    try:
        runner = MissionRunner(mission_id, user_id)
    except ValueError as e:
        return {"error": str(e)}
    _runners[key] = runner
    return runner.to_dict()


def execute_command(user_id: int, mission_id: str,
                    command: str) -> dict[str, Any]:
    """Execute a command and auto-validate objectives."""
    key = (user_id, mission_id)
    runner = _runners.get(key)
    if runner is None:
        return {"error": "No active mission. Start it first."}
    result = runner.execute(command)
    # Auto-save.
    _state[key] = runner.save_state()
    # Award XP for newly completed objectives.
    for v in result.get("validations", []):
        if v.get("passed"):
            _try_award_xp(user_id, v.get("xp", 0))
    return result


def get_hint(user_id: int, mission_id: str,
             objective_id: str) -> dict[str, Any]:
    key = (user_id, mission_id)
    runner = _runners.get(key)
    if runner is None:
        return {"hint": "Start the mission first."}
    hint = runner.use_hint(objective_id)
    _state[key] = runner.save_state()
    return {"hint": hint, "objective_id": objective_id}


def get_progress(user_id: int,
                 mission_id: str) -> dict[str, Any] | None:
    key = (user_id, mission_id)
    runner = _runners.get(key)
    if runner:
        return runner.to_dict()
    return None


def reset_mission(user_id: int,
                  mission_id: str) -> dict[str, Any]:
    key = (user_id, mission_id)
    _runners.pop(key, None)
    _state.pop(key, None)
    return start_mission(user_id, mission_id)


def ai_context(user_id: int,
               mission_id: str) -> dict[str, Any]:
    runner = _runners.get((user_id, mission_id))
    if runner:
        return runner.ai_context()
    return {}


def available_missions(category: str | None = None
                       ) -> list[dict[str, Any]]:
    return list_missions()


def _try_award_xp(user_id: int, xp: int) -> None:
    if xp <= 0:
        return
    try:
        from app.auth.models import User
        from app.extensions import db
        user = User.query.get(user_id)
        if user and hasattr(user, "xp"):
            user.xp = (user.xp or 0) + xp
            db.session.commit()
    except (ImportError, AttributeError, RuntimeError):
        pass
