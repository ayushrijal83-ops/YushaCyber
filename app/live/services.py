"""Live classroom services — CRUD, enrollment, attendance."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.extensions import db
from app.live.models import (
    ClassResource, Enrollment, LiveClass,
)


# ── Class CRUD ──
def create_class(instructor_id: int, title: str, slug: str,
                 **kwargs: Any) -> LiveClass:
    lc = LiveClass(instructor_id=instructor_id, title=title,
                   slug=slug, **kwargs)
    db.session.add(lc)
    db.session.flush()
    return lc


def update_class(lc: LiveClass, data: dict[str, Any]) -> LiveClass:
    for key in ("title", "description", "category", "difficulty",
                "start_time", "end_time", "timezone", "capacity",
                "meeting_provider", "meeting_url", "meeting_room",
                "visibility", "status", "recurring_rule"):
        if key in data:
            setattr(lc, key, data[key])
    db.session.flush()
    return lc


def delete_class(lc: LiveClass) -> None:
    db.session.delete(lc)
    db.session.flush()


def get_by_slug(slug: str) -> LiveClass | None:
    return LiveClass.query.filter_by(slug=slug).first()


def upcoming(limit: int = 20) -> list[LiveClass]:
    now = datetime.now(timezone.utc)
    return (LiveClass.query
            .filter(LiveClass.status.in_(("scheduled", "live")))
            .filter(LiveClass.start_time >= now)
            .order_by(LiveClass.start_time)
            .limit(limit).all())


def start_class(lc: LiveClass) -> LiveClass:
    lc.status = "live"
    if not lc.meeting_url:
        from app.live.providers import generate_url
        lc.meeting_url = generate_url(lc)
    db.session.flush()
    return lc


def end_class(lc: LiveClass) -> LiveClass:
    lc.status = "ended"
    db.session.flush()
    return lc


# ── Enrollment ──
def enroll(user_id: int, class_id: int) -> Enrollment | None:
    lc = LiveClass.query.get(class_id)
    if lc is None or lc.is_full:
        return None
    existing = Enrollment.query.filter_by(
        user_id=user_id, class_id=class_id).first()
    if existing:
        return existing
    e = Enrollment(user_id=user_id, class_id=class_id)
    db.session.add(e)
    db.session.flush()
    return e


def unenroll(user_id: int, class_id: int) -> bool:
    e = Enrollment.query.filter_by(
        user_id=user_id, class_id=class_id).first()
    if e is None:
        return False
    db.session.delete(e)
    db.session.flush()
    return True


def is_enrolled(user_id: int, class_id: int) -> bool:
    return Enrollment.query.filter_by(
        user_id=user_id, class_id=class_id).first() is not None


def enrolled_classes(user_id: int) -> list[LiveClass]:
    enrollments = Enrollment.query.filter_by(user_id=user_id).all()
    return [e.live_class for e in enrollments if e.live_class]


# ── Attendance ──
def mark_joined(user_id: int, class_id: int) -> Enrollment | None:
    e = Enrollment.query.filter_by(
        user_id=user_id, class_id=class_id).first()
    if e is None:
        return None
    now = datetime.now(timezone.utc)
    e.joined_at = now
    lc = e.live_class
    if lc and lc.start_time:
        start = lc.start_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        delta = (now - start).total_seconds()
        e.attendance_status = "late" if delta > 600 else "present"
    else:
        e.attendance_status = "present"
    db.session.flush()
    return e


def mark_left(user_id: int, class_id: int) -> Enrollment | None:
    e = Enrollment.query.filter_by(
        user_id=user_id, class_id=class_id).first()
    if e is None:
        return None
    e.left_at = datetime.now(timezone.utc)
    if e.joined_at:
        joined = e.joined_at
        if joined.tzinfo is None:
            joined = joined.replace(tzinfo=timezone.utc)
        e.attendance_duration = int(
            (e.left_at - joined).total_seconds())
    db.session.flush()
    return e


def attendance_report(class_id: int) -> list[dict[str, Any]]:
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    return [{
        "user_id": e.user_id,
        "username": e.user.username if e.user else "",
        "status": e.attendance_status,
        "joined_at": str(e.joined_at) if e.joined_at else "",
        "left_at": str(e.left_at) if e.left_at else "",
        "duration": e.attendance_duration or 0,
    } for e in enrollments]


# ── Resources ──
def add_resource(class_id: int, title: str,
                 resource_type: str = "document",
                 url: str = "",
                 filename: str = "") -> ClassResource:
    r = ClassResource(class_id=class_id, title=title,
                      resource_type=resource_type,
                      url=url, filename=filename)
    db.session.add(r)
    db.session.flush()
    return r


# ── Calendar ──
def calendar_events(month: int | None = None,
                    year: int | None = None) -> list[dict[str, Any]]:
    q = LiveClass.query.filter(
        LiveClass.status.in_(("scheduled", "live")))
    if month and year:
        from calendar import monthrange
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        _, last_day = monthrange(year, month)
        end = datetime(year, month, last_day, 23, 59, 59,
                       tzinfo=timezone.utc)
        q = q.filter(LiveClass.start_time.between(start, end))
    classes = q.order_by(LiveClass.start_time).all()
    return [{
        "id": c.id, "title": c.title, "slug": c.slug,
        "start": str(c.start_time) if c.start_time else "",
        "end": str(c.end_time) if c.end_time else "",
        "status": c.status, "instructor": c.instructor.username,
        "category": c.category, "enrolled": c.enrolled_count,
        "capacity": c.capacity,
    } for c in classes]


def class_to_dict(lc: LiveClass, show_url: bool = False
                  ) -> dict[str, Any]:
    d = {
        "id": lc.id, "title": lc.title, "slug": lc.slug,
        "description": lc.description or "",
        "instructor": lc.instructor.username if lc.instructor else "",
        "category": lc.category, "difficulty": lc.difficulty,
        "start_time": str(lc.start_time) if lc.start_time else "",
        "end_time": str(lc.end_time) if lc.end_time else "",
        "status": lc.status,
        "enrolled": lc.enrolled_count, "capacity": lc.capacity,
        "provider": lc.meeting_provider,
        "resources": [{"title": r.title, "type": r.resource_type,
                       "url": r.url or ""}
                      for r in (lc.resources or [])],
    }
    if show_url and lc.status == "live":
        d["meeting_url"] = lc.meeting_url or ""
    return d
