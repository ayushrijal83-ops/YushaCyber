"""Lab engine — the main orchestrator.

Manages sessions, delegates to registry/workspace/objectives,
integrates with XP and achievement systems.
"""

from __future__ import annotations

from typing import Any

from app.core.lab_engine import state
from app.core.lab_engine.objective import ObjectiveResult
from app.core.lab_engine.registry import get_lab
from app.core.lab_engine.session import LabSession

# Active sessions: {(user_id, slug): LabSession}
_sessions: dict[tuple[int, str], LabSession] = {}


def start(user_id: int, slug: str) -> LabSession | None:
    """Start or resume a lab session."""
    lab = get_lab(slug)
    if lab is None:
        return None
    # Resume from saved state.
    saved = state.load(user_id, slug)
    if saved:
        session = LabSession.from_dict(saved, lab)
    else:
        session = LabSession(lab, user_id)
    _sessions[(user_id, slug)] = session
    return session


def get_session(user_id: int, slug: str) -> LabSession | None:
    return _sessions.get((user_id, slug))


def submit(user_id: int, slug: str,
           objective_id: str, submission: str = "",
           context: dict[str, Any] | None = None
           ) -> ObjectiveResult:
    """Submit for validation."""
    session = _sessions.get((user_id, slug))
    if session is None:
        return ObjectiveResult(message="No active session.")
    result = session.submit(objective_id, submission, context)
    # Auto-save.
    state.save(user_id, slug, session.to_dict())
    # Award XP via existing system if passed.
    if result.passed and result.xp_earned > 0:
        _award_xp(user_id, result.xp_earned)
    return result


def hint(user_id: int, slug: str,
         objective_id: str = "") -> None:
    session = _sessions.get((user_id, slug))
    if session:
        session.use_hint(objective_id)
        state.save(user_id, slug, session.to_dict())


def reset(user_id: int, slug: str) -> LabSession | None:
    _sessions.pop((user_id, slug), None)
    state.reset(user_id, slug)
    return start(user_id, slug)


def ai_context(user_id: int, slug: str) -> dict[str, Any]:
    """Get AI mentor context for the current session."""
    session = _sessions.get((user_id, slug))
    if session:
        return session.ai_context()
    return {}


def _award_xp(user_id: int, xp: int) -> None:
    """Award XP via existing system (graceful if unavailable)."""
    try:
        from app.auth.models import User
        from app.extensions import db
        user = User.query.get(user_id)
        if user and hasattr(user, "xp"):
            user.xp = (user.xp or 0) + xp
            db.session.commit()
    except Exception:  # noqa: BLE001
        pass  # graceful outside app context
