"""Cyber Labs service layer.

The single place lab data is read and written. Routes go through these
functions and never touch the ORM. Foundation only: starting or completing
a lab records progress — it does NOT award XP, unlock achievements, or
issue certificates (those integrations are later tickets).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from app.extensions import db
from app.labs.models import Lab, LabCategory, UserLabProgress


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def get_categories() -> list[LabCategory]:
    """All active lab categories in display order."""
    return (
        LabCategory.query
        .filter_by(is_active=True)
        .order_by(LabCategory.display_order)
        .all()
    )


def get_category(slug: str) -> Optional[LabCategory]:
    """One active category by slug, or None."""
    if not slug:
        return None
    return LabCategory.query.filter_by(slug=slug, is_active=True).first()


def get_labs() -> list[Lab]:
    """All active labs in (category, display) order."""
    return (
        Lab.query
        .filter_by(is_active=True)
        .order_by(Lab.category_id, Lab.display_order)
        .all()
    )


def get_lab(slug: str) -> Optional[Lab]:
    """One active lab by slug, or None."""
    if not slug:
        return None
    return Lab.query.filter_by(slug=slug, is_active=True).first()


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------
def _get_or_create_progress(user: User, lab: Lab) -> UserLabProgress:
    """Fetch a user's progress row for a lab, creating it if absent."""
    row = (
        UserLabProgress.query
        .filter_by(user_id=user.id, lab_id=lab.id)
        .first()
    )
    if row is None:
        row = UserLabProgress(
            user_id=user.id, lab_id=lab.id, started=False, completed=False
        )
        db.session.add(row)
    return row


def start_lab(user: User, lab: Lab) -> dict[str, Any]:
    """Mark a lab as started for a user (idempotent).

    Creates the progress row on first call and stamps ``started_at``.
    Calling again leaves the original start time intact. Returns
    {"ok": bool, "progress": row | None, "already_started": bool}.
    """
    result = {"ok": False, "progress": None, "already_started": False}
    if user is None or lab is None or not lab.is_active:
        result["error"] = "invalid"
        return result

    try:
        row = _get_or_create_progress(user, lab)
        already = bool(row.started)
        if not already:
            row.started = True
            row.started_at = _utcnow()
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to start lab: user %s lab %s", user.id, lab.id
        )
        result["error"] = "persist_failed"
        return result

    if not already:
        current_app.logger.info(
            "Lab started: user=%s lab=%s", user.id, lab.slug
        )
    result.update({"ok": True, "progress": row, "already_started": already})
    return result


def complete_lab(user: User, lab: Lab) -> dict[str, Any]:
    """Mark a lab as completed for a user (idempotent).

    Ensures the lab is started, stamps ``completed_at``, and records the
    elapsed ``time_spent_seconds`` when a start time exists. Completing an
    already-completed lab changes nothing. NO XP is awarded here — reward
    integration is a later ticket.

    Returns {"ok": bool, "progress": row | None, "already_completed": bool}.
    """
    result = {"ok": False, "progress": None, "already_completed": False}
    if user is None or lab is None or not lab.is_active:
        result["error"] = "invalid"
        return result

    try:
        row = _get_or_create_progress(user, lab)
        already = bool(row.completed)

        if not already:
            now = _utcnow()
            # A lab completed without an explicit start still counts as started.
            if not row.started:
                row.started = True
                row.started_at = now
            row.completed = True
            row.completed_at = now
            if row.started_at is not None:
                started_at = row.started_at
                if started_at.tzinfo is None:  # SQLite may return naive values
                    started_at = started_at.replace(tzinfo=timezone.utc)
                row.time_spent_seconds = max(
                    0, int((now - started_at).total_seconds())
                )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to complete lab: user %s lab %s", user.id, lab.id
        )
        result["error"] = "persist_failed"
        return result

    if not already:
        current_app.logger.info(
            "Lab completed: user=%s lab=%s time_spent=%ss",
            user.id, lab.slug, row.time_spent_seconds,
        )
    result.update({"ok": True, "progress": row, "already_completed": already})
    return result


def get_user_progress(user: User) -> list[UserLabProgress]:
    """A user's lab progress rows, most recently updated first."""
    if user is None:
        return []
    return (
        UserLabProgress.query
        .filter_by(user_id=user.id)
        .order_by(UserLabProgress.updated_at.desc())
        .all()
    )


# ===========================================================================
# Lab Engine orchestration (YC-012.1)
#
# The ONLY place that ties together: simulator (world behaviour), validator
# (judging objectives), session manager (state), progress and XP. Routes call
# into here and nothing else. Nothing below knows what a "Linux" lab is.
# ===========================================================================
def _objective_view(objective, completed: bool) -> dict[str, Any]:
    """An objective as plain data for the UI (never leaks the validator spec)."""
    return {
        "id": objective.id,
        "title": objective.title,
        "instruction": objective.instruction or objective.description or "",
        "order": objective.display_order,
        "xp_reward": objective.xp_reward,
        "optional": objective.is_optional,
        "hints": objective.hints(),
        "completed": completed,
    }


def get_objectives(lab) -> list:
    """A lab's objectives in display order."""
    from app.labs.models import LabObjective
    return (
        LabObjective.query
        .filter_by(lab_id=lab.id)
        .order_by(LabObjective.display_order)
        .all()
    )


def _completed_objective_ids(user, lab) -> set[int]:
    from app.labs.models import LabObjective, UserObjectiveProgress
    rows = (
        db.session.query(UserObjectiveProgress.objective_id)
        .join(LabObjective, LabObjective.id == UserObjectiveProgress.objective_id)
        .filter(
            UserObjectiveProgress.user_id == user.id,
            UserObjectiveProgress.completed.is_(True),
            LabObjective.lab_id == lab.id,
        )
        .all()
    )
    return {r[0] for r in rows}


def _complete_objective(user, objective) -> int:
    """Mark an objective complete and award its XP ONCE. Returns XP awarded."""
    from app.labs.models import UserObjectiveProgress

    row = UserObjectiveProgress.query.filter_by(
        user_id=user.id, objective_id=objective.id
    ).first()
    if row is not None and row.completed:
        return 0  # already earned — never award twice

    if row is None:
        row = UserObjectiveProgress(user_id=user.id, objective_id=objective.id)
        db.session.add(row)
    row.completed = True
    row.completed_at = _utcnow()

    awarded = 0
    if objective.xp_reward:
        # Reuse the existing XP engine — never touch user.xp directly.
        from app.dashboard.services import award_xp
        award_xp(user, objective.xp_reward)
        awarded = objective.xp_reward
    else:
        db.session.commit()
    return awarded


def execute_action(user, lab, action_type: str,
                   payload: dict[str, Any]) -> dict[str, Any]:
    """The engine spine: run one action, judge objectives, award XP, persist.

    Simulator-agnostic: works identically for a terminal command, an
    inspector selection or a future packet-viewer flag.
    """
    from app.labs import session_manager
    from app.labs.simulator_base import Action
    from app.labs.validator import ValidationContext, validate

    if user is None or lab is None or not lab.is_active:
        return {"ok": False, "error": "invalid"}
    if not lab.is_interactive:
        return {"ok": False, "error": "not_interactive"}

    simulator = session_manager.get_simulator(lab)
    session = session_manager.start_session(user, lab)
    state = session_manager.load_state(session, simulator, lab)

    action = Action(type=action_type, payload=payload or {})
    result = simulator.handle(state, action)

    # --- Objective engine: judge only the not-yet-completed objectives ---
    ctx = ValidationContext(
        action=action, output=result.output,
        state=result.new_state, events=result.events,
    )
    done_ids = _completed_objective_ids(user, lab)
    newly_completed: list[dict[str, Any]] = []
    xp_awarded = 0

    for objective in get_objectives(lab):
        if objective.id in done_ids:
            continue
        if validate(objective.validator_type, objective.get_validator_data(), ctx):
            xp_awarded += _complete_objective(user, objective)
            newly_completed.append({
                "id": objective.id, "title": objective.title,
                "xp": objective.xp_reward,
            })

    session_manager.save_state(session, result.new_state)

    # --- Lab-level roll-up + completion XP (award-once) ---
    lab_completed = _sync_lab_completion(user, lab)

    # --- Reuse the existing achievement engine (no new achievement logic) ---
    if newly_completed or lab_completed:
        try:
            from app.achievement.services import check_and_unlock_achievements
            check_and_unlock_achievements(user)
        except Exception:  # noqa: BLE001 — never fail a lab action on this
            current_app.logger.exception(
                "Achievement check failed after lab action: user %s", user.id
            )

    # --- Reuse the existing certificate engine (YC-031.0, additive) ---
    if lab_completed:
        try:
            from app.certificates.services import check_all_certificates
            check_all_certificates(user)
        except Exception:  # noqa: BLE001 — never fail a lab action on this
            current_app.logger.exception(
                "Certificate check failed after lab action: user %s", user.id
            )

    if newly_completed:
        current_app.logger.info(
            "Lab objectives completed: user=%s lab=%s objectives=%s xp=%s",
            user.id, lab.slug, [o["id"] for o in newly_completed], xp_awarded,
        )

    # YC-026.5: resolve next lab + session stats for the results screen.
    next_lab_url = None
    commands_used = 0
    achievements_earned = []
    if lab_completed:
        next_lab = Lab.query.filter_by(
            prerequisite_lab_id=lab.id, is_active=True
        ).first()
        if next_lab:
            from flask import url_for
            next_lab_url = url_for("labs.detail", slug=next_lab.slug)
        # Session stats
        commands_used = result.new_state.get("flags", {}).get("commands_used", 0)
        # Achievements that were unlocked by the XP/milestone from this lab
        from app.achievement.models import UserAchievement
        recent = (UserAchievement.query.filter_by(user_id=user.id)
                  .order_by(UserAchievement.unlocked_at.desc()).limit(5).all())
        for ua in recent:
            achievements_earned.append({
                "title": ua.achievement.title,
                "icon": ua.achievement.icon,
                "xp": ua.achievement.bonus_xp,
            })

    return {
        "ok": True,
        "output": result.output,
        "clear": result.clear,
        "prompt": simulator.prompt(result.new_state),
        "status": simulator.status_panel(result.new_state),
        "objectives": get_objective_views(user, lab),
        "newly_completed": newly_completed,
        "xp_awarded": xp_awarded,
        "lab_completed": lab_completed,
        "next_lab_url": next_lab_url,
        "commands_used": commands_used,
        "achievements_earned": achievements_earned,
    }


def _sync_lab_completion(user, lab) -> bool:
    """Mark the lab complete when all required objectives are done.

    Awards lab.xp_reward exactly ONCE, on the first completion — the same
    award-once rule proven by quizzes (YC-007.4) and CTF (YC-010.4).
    Note: complete_lab() from YC-011.1 records progress but deliberately
    awards no XP, so the engine owns the reward here.
    """
    objectives = [o for o in get_objectives(lab) if not o.is_optional]
    if not objectives:
        return False
    done = _completed_objective_ids(user, lab)
    if not all(o.id in done for o in objectives):
        return False

    # Capture prior state BEFORE recording completion, so a first completion
    # is distinguishable from a repeat.
    result = complete_lab(user, lab)
    if not result.get("ok"):
        return False
    if result.get("already_completed"):
        return False  # already rewarded — never award twice

    if lab.xp_reward:
        from app.dashboard.services import award_xp
        award_xp(user, lab.xp_reward)  # existing XP engine; never touch user.xp

    current_app.logger.info(
        "Lab completed: user=%s lab=%s xp_awarded=%s",
        user.id, lab.slug, lab.xp_reward,
    )
    return True


def get_objective_views(user, lab) -> list[dict[str, Any]]:
    """Objectives with this user's completion state (plain dicts for the UI)."""
    done = _completed_objective_ids(user, lab)
    return [_objective_view(o, o.id in done) for o in get_objectives(lab)]


def get_workspace_context(user, lab) -> dict[str, Any]:
    """Everything the interactive lab page needs — no ORM leaks."""
    from app.labs import session_manager

    simulator = session_manager.get_simulator(lab)
    session = session_manager.start_session(user, lab)
    state = session_manager.load_state(session, simulator, lab)

    return {
        "capabilities": sorted(simulator.capabilities()),
        "prompt": simulator.prompt(state),
        "welcome": simulator.welcome(state),
        "status": simulator.status_panel(state),
        "ui": simulator.describe_ui(),
        "objectives": get_objective_views(user, lab),
    }


def reset_lab_session(user, lab) -> dict[str, Any]:
    """Reset the simulated state. Objective/XP history is preserved."""
    from app.labs import session_manager

    if user is None or lab is None or not lab.is_interactive:
        return {"ok": False, "error": "invalid"}
    session = session_manager.reset_session(user, lab)
    simulator = session_manager.get_simulator(lab)
    state = session.get_state()
    current_app.logger.info("Lab session reset: user=%s lab=%s", user.id, lab.slug)
    return {
        "ok": True,
        "objectives": get_objective_views(user, lab),
        "prompt": simulator.prompt(state),
        "welcome": simulator.welcome(state),
        "status": simulator.status_panel(state),
    }


# ===========================================================================
# Sequential progression + track view (YC-012.3)
# ===========================================================================
def is_lab_completed(user, lab) -> bool:
    """Whether the user has completed a lab (lab-level roll-up)."""
    if user is None or lab is None:
        return False
    from app.labs.models import UserLabProgress
    row = UserLabProgress.query.filter_by(
        user_id=user.id, lab_id=lab.id, completed=True
    ).first()
    return row is not None


def is_lab_unlocked(user, lab) -> bool:
    """A lab is unlocked when it has no prerequisite, or the prerequisite is
    completed by this user. Data-driven — works for any future track."""
    if lab is None:
        return False
    if not lab.prerequisite_lab_id:
        return True
    from app.labs.models import Lab
    prereq = Lab.query.filter_by(id=lab.prerequisite_lab_id).first()
    return is_lab_completed(user, prereq) if prereq else True


def get_track_context(user, category_slug: str = "linux") -> dict[str, Any]:
    """Progress across a whole track: labs with lock/complete state + totals."""
    from app.labs.models import Lab, LabCategory

    category = LabCategory.query.filter_by(slug=category_slug).first()
    if category is None:
        return {"labs": [], "completed": 0, "total": 0,
                "percent": 0, "total_xp": 0, "earned_xp": 0}

    labs = (
        Lab.query
        .filter_by(category_id=category.id, is_active=True, is_interactive=True)
        .order_by(Lab.display_order)
        .all()
    )

    rows = []
    completed = earned_xp = total_xp = 0
    for lab in labs:
        done = is_lab_completed(user, lab)
        unlocked = is_lab_unlocked(user, lab)
        total_xp += lab.xp_reward or 0
        if done:
            completed += 1
            earned_xp += lab.xp_reward or 0
        rows.append({
            "title": lab.title, "slug": lab.slug,
            "difficulty": lab.difficulty, "xp_reward": lab.xp_reward,
            "estimated_minutes": lab.estimated_minutes,
            "order": lab.display_order,
            "completed": done, "unlocked": unlocked,
            "is_challenge": lab.slug.endswith("-challenge"),
        })

    total = len(labs)
    return {
        "category": {"name": category.name, "slug": category.slug},
        "labs": rows,
        "completed": completed,
        "remaining": total - completed,
        "total": total,
        "percent": int(completed / total * 100) if total else 0,
        "total_xp": total_xp,
        "earned_xp": earned_xp,
    }
