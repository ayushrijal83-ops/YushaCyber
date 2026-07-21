"""Assignment Engine (YC-034.0).

Assignments point at EXISTING content (roadmaps, lessons, labs, CTF
challenges, quizzes) and their completion is resolved live from the
existing progress tables — a student who completed the lab last week
is already "done" the moment the assignment is created. Due dates are
compared against the completion timestamps those systems already
store, which is how "late" is decided.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.community import notification_engine
from app.community.models import ASSIGNMENT_SUBJECTS, Assignment, Classroom
from app.ctf.models import Challenge, ChallengeSolve
from app.extensions import db
from app.labs.models import Lab, UserLabProgress
from app.roadmap.models import (
    Lesson,
    Quiz,
    RoadmapCategory,
    RoadmapModule,
    UserLessonProgress,
    UserQuizAttempt,
)


class AssignmentError(ValueError):
    """User-facing assignment rule violation."""


def subject_catalog() -> dict[str, list[tuple[int, str]]]:
    """Everything a teacher can assign, as (id, label) per subject type."""
    lessons = (db.session.query(Lesson.id, Lesson.title,
                                RoadmapModule.title)
               .join(RoadmapModule,
                     RoadmapModule.id == Lesson.module_id)
               .order_by(RoadmapModule.display_order,
                         Lesson.display_order).all())
    return {
        "roadmap": [(c.id, c.title) for c in
                    RoadmapCategory.query.order_by(
                        RoadmapCategory.display_order).all()],
        "lesson": [(lid, f"{module} — {title}")
                   for lid, title, module in lessons],
        "lab": [(lab.id, lab.title) for lab in
                Lab.query.filter_by(is_active=True)
                .order_by(Lab.title).all()],
        "ctf": [(ch.id, ch.title) for ch in
                Challenge.query.filter_by(is_active=True)
                .order_by(Challenge.title).all()],
        "quiz": [(q.id, q.title) for q in
                 Quiz.query.filter_by(is_active=True)
                 .order_by(Quiz.title).all()],
    }


_SUBJECT_MODEL = {"roadmap": RoadmapCategory, "lesson": Lesson,
                  "lab": Lab, "ctf": Challenge, "quiz": Quiz}


def create_assignment(classroom: Classroom, creator_id: int,
                      subject_type: str, subject_id: int,
                      instructions: str = "",
                      due_at: datetime | None = None) -> Assignment:
    if subject_type not in ASSIGNMENT_SUBJECTS:
        raise AssignmentError("Unknown assignment type.")
    subject = db.session.get(_SUBJECT_MODEL[subject_type], subject_id)
    if subject is None:
        raise AssignmentError("That content does not exist.")
    title = getattr(subject, "title", f"{subject_type} #{subject_id}")

    assignment = Assignment(
        classroom_id=classroom.id, subject_type=subject_type,
        subject_id=subject_id, title=title,
        instructions=(instructions or "").strip() or None,
        due_at=due_at, created_by=creator_id)
    db.session.add(assignment)
    due_note = (f" Due {due_at.date().isoformat()}."
                if due_at else "")
    notification_engine.notify(
        [m.user_id for m in classroom.members], "assignment_new",
        f"New assignment: {title}",
        f"{subject_type.capitalize()} assigned in "
        f"“{classroom.name}”.{due_note}",
        f"/classrooms/{classroom.id}")
    db.session.commit()
    return assignment


# ===========================================================================
# Live completion resolution
# ===========================================================================
def _completions(assignment: Assignment,
                 user_ids: list[int]) -> dict[int, datetime | None]:
    """user_id -> completion timestamp (None = not completed)."""
    subject_id = assignment.subject_id
    kind = assignment.subject_type

    if kind == "lesson":
        rows = db.session.query(
            UserLessonProgress.user_id, UserLessonProgress.completed_at
        ).filter(UserLessonProgress.lesson_id == subject_id,
                 UserLessonProgress.user_id.in_(user_ids),
                 UserLessonProgress.completed.is_(True)).all()
        return dict(rows)

    if kind == "lab":
        rows = db.session.query(
            UserLabProgress.user_id, UserLabProgress.completed_at
        ).filter(UserLabProgress.lab_id == subject_id,
                 UserLabProgress.user_id.in_(user_ids),
                 UserLabProgress.completed.is_(True)).all()
        return dict(rows)

    if kind == "ctf":
        rows = db.session.query(
            ChallengeSolve.user_id, ChallengeSolve.solved_at
        ).filter(ChallengeSolve.challenge_id == subject_id,
                 ChallengeSolve.user_id.in_(user_ids),
                 ChallengeSolve.solved.is_(True)).all()
        return dict(rows)

    if kind == "quiz":
        rows = db.session.query(
            UserQuizAttempt.user_id,
            db.func.min(UserQuizAttempt.completed_at)
        ).filter(UserQuizAttempt.quiz_id == subject_id,
                 UserQuizAttempt.user_id.in_(user_ids),
                 UserQuizAttempt.passed.is_(True)) \
            .group_by(UserQuizAttempt.user_id).all()
        return dict(rows)

    # roadmap: ALL lessons under the category must be completed;
    # completion time = the last lesson's completion.
    lesson_ids = [lid for (lid,) in
                  db.session.query(Lesson.id)
                  .join(RoadmapModule,
                        RoadmapModule.id == Lesson.module_id)
                  .filter(RoadmapModule.category_id == subject_id).all()]
    if not lesson_ids:
        return {}
    rows = db.session.query(
        UserLessonProgress.user_id,
        db.func.count(UserLessonProgress.id),
        db.func.max(UserLessonProgress.completed_at)
    ).filter(UserLessonProgress.lesson_id.in_(lesson_ids),
             UserLessonProgress.user_id.in_(user_ids),
             UserLessonProgress.completed.is_(True)) \
        .group_by(UserLessonProgress.user_id).all()
    return {uid: last for uid, count, last in rows
            if count == len(lesson_ids)}


def _is_late(completed_at: datetime | None,
             due_at: datetime | None) -> bool:
    if completed_at is None or due_at is None:
        return False
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    return completed_at > due_at


def status_for(assignment: Assignment,
               user_ids: list[int]) -> dict[int, dict[str, Any]]:
    """user_id -> {done, completed_at, late, overdue} for one assignment."""
    completions = _completions(assignment, user_ids)
    now = datetime.now(timezone.utc)
    due = assignment.due_at
    if due is not None and due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)

    statuses: dict[int, dict[str, Any]] = {}
    for uid in user_ids:
        completed_at = completions.get(uid)
        done = completed_at is not None or uid in completions
        statuses[uid] = {
            "done": done,
            "completed_at": completed_at,
            "late": _is_late(completed_at, assignment.due_at),
            "overdue": (not done and due is not None and now > due),
        }
    return statuses
