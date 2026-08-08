"""Mission services — public API with state persistence."""

from __future__ import annotations

from typing import Any

from app.core.missions.mission_loader import MISSIONS, get_mission, list_missions
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
            _sync_record(user_id, runner)
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
    _state[key] = runner.save_state()
    _sync_record(user_id, runner)
    _try_ai_hook("on_lab_start", user_id, mission_id)
    return runner.to_dict()


def execute_command(user_id: int, mission_id: str,
                    command: str) -> dict[str, Any]:
    """Execute a command and auto-validate objectives."""
    key = (user_id, mission_id)
    runner = _runners.get(key)
    if runner is None:
        return {"error": "No active mission. Start it first."}
    was_completed = runner.progress.completed
    result = runner.execute(command)
    # Auto-save.
    _state[key] = runner.save_state()
    _sync_record(user_id, runner)

    # Award XP for newly completed objectives + notify the AI mentor.
    for v in result.get("validations", []):
        if v.get("passed"):
            _try_award_xp(user_id, v.get("xp", 0))
            _try_ai_hook("on_objective_complete", user_id, v.get("objective_id", ""))

    if runner.progress.completed and not was_completed:
        _try_ai_hook("on_lab_complete", user_id, mission_id)
        _try_award_achievements(user_id)

    return result


def get_hint(user_id: int, mission_id: str,
             objective_id: str) -> dict[str, Any]:
    key = (user_id, mission_id)
    runner = _runners.get(key)
    if runner is None:
        return {"hint": "Start the mission first."}
    hint = runner.use_hint(objective_id)
    _state[key] = runner.save_state()
    _sync_record(user_id, runner)
    _try_ai_hook("on_hint_used", user_id)
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


# ═══════════════════════════════════════════════════════════
# Discovery / status helpers (YC-034.3 — Interactive Missions UI)
# ═══════════════════════════════════════════════════════════
def mission_status(user_id: int, mission_id: str,
                   mission: dict[str, Any] | None = None) -> str:
    """One of 'locked' / 'available' / 'in_progress' / 'completed'."""
    from app.core.missions.models import STATUS_COMPLETED, get_record

    record = get_record(user_id, mission_id)
    if record is not None:
        return record.status

    mission = mission or get_mission(mission_id)
    if mission is None:
        return "locked"
    prereq = _prerequisite_for(mission_id)
    if prereq is None:
        return "available"
    prereq_record = get_record(user_id, prereq)
    if prereq_record is not None and prereq_record.status == STATUS_COMPLETED:
        return "available"
    return "locked"


def list_missions_with_status(user_id: int) -> list[dict[str, Any]]:
    """Discovery-page payload: every mission plus this user's status/progress."""
    from app.core.missions.models import get_record

    out: list[dict[str, Any]] = []
    for mid, m in MISSIONS.items():
        record = get_record(user_id, mid)
        total = len(m["objectives"])
        completed_n = record.objectives_completed if record else 0
        out.append({
            "id": mid,
            "title": m["title"],
            "description": m["description"],
            "category": m.get("category", "linux"),
            "difficulty": m["difficulty"],
            "estimated_minutes": m["estimated_minutes"],
            "xp_total": m["xp_total"],
            "objective_count": total,
            "status": mission_status(user_id, mid, m),
            "objectives_completed": completed_n,
            "pct": int(completed_n / max(1, total) * 100),
            "prerequisite": _prerequisite_for(mid),
        })
    return out


def dashboard_stats(user_id: int) -> dict[str, Any]:
    """Aggregate stats for the Interactive Missions header."""
    from app.core.missions.models import STATUS_COMPLETED, MissionRecord

    missions = list_missions_with_status(user_id)
    available = sum(1 for m in missions if m["status"] != "locked")
    completed = sum(1 for m in missions if m["status"] == STATUS_COMPLETED)
    xp_earned = sum(r.xp_earned for r in
                    MissionRecord.query.filter_by(user_id=user_id).all())
    streak = 0
    try:
        from app.auth.models import User
        user = User.query.get(user_id)
        streak = getattr(user, "streak", 0) or 0
    except (ImportError, AttributeError, RuntimeError):
        pass
    return {
        "available_missions": available,
        "completed_missions": completed,
        "xp_earned": xp_earned,
        "streak": streak,
    }


def _prerequisite_for(mission_id: str) -> str | None:
    for mid, m in MISSIONS.items():
        if m.get("next_mission") == mission_id:
            return mid
    return None


# ═══════════════════════════════════════════════════════════
# Internal helpers — best-effort side effects, never fatal to the
# in-memory mission session if the DB/AI layer is unavailable.
# ═══════════════════════════════════════════════════════════
def _sync_record(user_id: int, runner: MissionRunner) -> None:
    try:
        from datetime import datetime, timezone

        from app.core.missions.models import upsert_progress
        started_at = (datetime.fromtimestamp(runner.progress.started_at, tz=timezone.utc)
                     if runner.progress.started_at else None)
        upsert_progress(
            user_id, runner.progress.mission_id,
            total=runner.progress.total,
            completed=len(runner.progress.completed_ids),
            xp_earned=runner.progress.xp_earned,
            hints_used=runner.progress.hints_used,
            attempts=runner.progress.attempts,
            is_complete=runner.progress.completed,
            started_at=started_at,
        )
    except (ImportError, AttributeError, RuntimeError):
        pass


def _try_award_xp(user_id: int, xp: int) -> None:
    if xp <= 0:
        return
    try:
        from app.auth.models import User
        from app.dashboard.services import award_xp
        user = User.query.get(user_id)
        if user:
            award_xp(user, xp)
    except (ImportError, AttributeError, RuntimeError):
        pass


def _try_award_achievements(user_id: int) -> None:
    try:
        from app.core.achievement.services import award_multiple
        award_multiple(user_id, {})
    except (ImportError, AttributeError, RuntimeError):
        pass


def _try_ai_hook(hook_name: str, *args: Any) -> None:
    try:
        from app.core.ai.context_engine import session as ai_session
        getattr(ai_session, hook_name)(*args)
    except (ImportError, AttributeError, RuntimeError):
        pass
