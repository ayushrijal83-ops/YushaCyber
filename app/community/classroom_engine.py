"""Classroom Engine (YC-034.0).

Classroom lifecycle (teachers create; students join by code or are
added by username) and the per-student progress board the teacher
sees — completion, XP, level, certificates, average quiz score and
time spent, all read live from the existing progress tables.

"Teacher" means an admin or a user with role ``mentor`` (set via the
new ``flask set-role`` CLI command).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func

from app.auth.models import User
from app.certificates.models import UserCertificate
from app.community import assignment_engine, notification_engine
from app.community.models import Announcement, Classroom, ClassroomMember
from app.ctf.models import ChallengeSolve
from app.extensions import db
from app.labs.models import UserLabProgress
from app.roadmap.models import UserLessonProgress, UserQuizAttempt


class ClassroomError(ValueError):
    """User-facing classroom rule violation."""


def is_teacher(user) -> bool:
    return bool(getattr(user, "is_admin", False)
                or getattr(user, "role", "") == "mentor")


def can_manage(user, classroom: Classroom) -> bool:
    return user.is_admin or classroom.teacher_id == user.id


def can_view(user, classroom: Classroom) -> bool:
    if can_manage(user, classroom):
        return True
    return ClassroomMember.query.filter_by(
        classroom_id=classroom.id, user_id=user.id).first() is not None


def create_classroom(teacher: User, name: str,
                     description: str = "") -> Classroom:
    if not is_teacher(teacher):
        raise ClassroomError("Only teachers can create classrooms.")
    name = (name or "").strip()
    if not 3 <= len(name) <= 80:
        raise ClassroomError("Classroom name must be 3–80 characters.")
    classroom = Classroom(name=name,
                          description=(description or "").strip() or None,
                          teacher_id=teacher.id)
    db.session.add(classroom)
    db.session.commit()
    return classroom


def join_by_code(user: User, code: str) -> Classroom:
    classroom = Classroom.query.filter_by(
        join_code=(code or "").strip().upper(), is_active=True).first()
    if not classroom:
        raise ClassroomError("No classroom with that join code.")
    _enroll(classroom, user)
    db.session.commit()
    return classroom


def add_student(classroom: Classroom, actor: User,
                username: str) -> User:
    if not can_manage(actor, classroom):
        raise ClassroomError("Only the teacher can add students.")
    student = User.query.filter(
        func.lower(User.username) == (username or "").strip().lower()
    ).first()
    if not student:
        raise ClassroomError("No user with that username.")
    _enroll(classroom, student)
    notification_engine.notify(
        [student.id], "classroom_added",
        f"You were added to “{classroom.name}”",
        f"Teacher: {classroom.teacher.username}. Assignments and "
        "announcements will appear here.",
        f"/classrooms/{classroom.id}")
    db.session.commit()
    return student


def _enroll(classroom: Classroom, user: User) -> None:
    if user.id == classroom.teacher_id:
        raise ClassroomError("The teacher is not enrolled as a student.")
    exists = ClassroomMember.query.filter_by(
        classroom_id=classroom.id, user_id=user.id).first()
    if exists:
        raise ClassroomError("Already enrolled in this classroom.")
    db.session.add(ClassroomMember(classroom_id=classroom.id,
                                   user_id=user.id))


def leave(classroom: Classroom, user: User) -> None:
    member = ClassroomMember.query.filter_by(
        classroom_id=classroom.id, user_id=user.id).first()
    if not member:
        raise ClassroomError("You are not enrolled in this classroom.")
    db.session.delete(member)
    db.session.commit()


def post_announcement(actor: User, title: str, body: str,
                      classroom: Classroom | None = None) -> Announcement:
    """Classroom announcement (its teacher) or global (admin only)."""
    title = (title or "").strip()
    body = (body or "").strip()
    if not title or not body:
        raise ClassroomError("Announcements need a title and a body.")
    if classroom is None:
        if not actor.is_admin:
            raise ClassroomError(
                "Only admins can post global announcements.")
        audience = [uid for (uid,) in db.session.query(User.id)
                    .filter(User.id != actor.id).all()]
        link = "/announcements"
    else:
        if not can_manage(actor, classroom):
            raise ClassroomError(
                "Only the teacher can post to this classroom.")
        audience = [m.user_id for m in classroom.members]
        link = f"/classrooms/{classroom.id}"

    announcement = Announcement(
        author_id=actor.id, title=title, body=body,
        classroom_id=classroom.id if classroom else None)
    db.session.add(announcement)
    notification_engine.notify(
        audience, "announcement", f"📣 {title}",
        body[:200], link)
    db.session.commit()
    return announcement


# ===========================================================================
# Teacher progress board
# ===========================================================================
def progress_board(classroom: Classroom) -> list[dict[str, Any]]:
    """One row per student: assignment completion, XP, level, certs,
    average quiz score, time spent — batch aggregate queries, no N+1."""
    student_ids = [m.user_id for m in classroom.members]
    if not student_ids:
        return []

    assignments = classroom.assignments
    done_map: dict[int, int] = {uid: 0 for uid in student_ids}
    for assignment in assignments:
        statuses = assignment_engine.status_for(assignment, student_ids)
        for uid, status in statuses.items():
            if status["done"]:
                done_map[uid] += 1

    certs = dict(db.session.query(
        UserCertificate.user_id, func.count(UserCertificate.id))
        .filter(UserCertificate.user_id.in_(student_ids))
        .group_by(UserCertificate.user_id).all())
    quiz_avg = dict(db.session.query(
        UserQuizAttempt.user_id, func.avg(UserQuizAttempt.percentage))
        .filter(UserQuizAttempt.user_id.in_(student_ids))
        .group_by(UserQuizAttempt.user_id).all())
    lesson_time = dict(db.session.query(
        UserLessonProgress.user_id,
        func.coalesce(func.sum(UserLessonProgress.time_spent), 0))
        .filter(UserLessonProgress.user_id.in_(student_ids))
        .group_by(UserLessonProgress.user_id).all())
    lab_time = dict(db.session.query(
        UserLabProgress.user_id,
        func.coalesce(func.sum(UserLabProgress.time_spent_seconds), 0))
        .filter(UserLabProgress.user_id.in_(student_ids))
        .group_by(UserLabProgress.user_id).all())
    quiz_time = dict(db.session.query(
        UserQuizAttempt.user_id,
        func.coalesce(func.sum(UserQuizAttempt.time_taken_seconds), 0))
        .filter(UserQuizAttempt.user_id.in_(student_ids))
        .group_by(UserQuizAttempt.user_id).all())
    ctf_time = dict(db.session.query(
        ChallengeSolve.user_id,
        func.coalesce(func.sum(ChallengeSolve.time_taken_seconds), 0))
        .filter(ChallengeSolve.user_id.in_(student_ids))
        .group_by(ChallengeSolve.user_id).all())

    total = len(assignments)
    rows = []
    for member in classroom.members:
        user = member.user
        done = done_map.get(user.id, 0)
        rows.append({
            "user": user,
            "assignments_done": done,
            "assignments_total": total,
            "completion_pct": round(100 * done / total) if total else 0,
            "xp": user.xp,
            "level": user.level,
            "certificates": certs.get(user.id, 0),
            "avg_score": round(float(quiz_avg.get(user.id) or 0), 1),
            "time_spent_seconds": int(
                (lesson_time.get(user.id) or 0)
                + (lab_time.get(user.id) or 0)
                + (quiz_time.get(user.id) or 0)
                + (ctf_time.get(user.id) or 0)),
        })
    rows.sort(key=lambda r: r["xp"], reverse=True)
    return rows
