"""Session management for the context engine."""

from __future__ import annotations

from app.core.ai.context_engine import activity, tracker
from app.core.ai.context_engine.builder import invalidate


def on_page_visit(user_id: int, path: str,
                  lab: str = "", lesson: str = "") -> None:
    """Call on every authenticated page load."""
    tracker.visit_page(user_id, path)
    activity.track(user_id, "page_visit", page=path,
                   lab=lab, lesson=lesson)


def on_lab_start(user_id: int, lab_slug: str) -> None:
    activity.track(user_id, "lab_start", lab=lab_slug)
    invalidate(user_id)


def on_objective_complete(user_id: int, objective: str) -> None:
    activity.track(user_id, "objective_complete")
    invalidate(user_id)


def on_hint_used(user_id: int) -> None:
    activity.track(user_id, "hint_used")


def on_answer_submitted(user_id: int, passed: bool) -> None:
    action = "answer_passed" if passed else "answer_failed"
    activity.track(user_id, action)


def on_lab_complete(user_id: int, lab_slug: str) -> None:
    activity.track(user_id, "lab_complete", lab=lab_slug)
    invalidate(user_id)
