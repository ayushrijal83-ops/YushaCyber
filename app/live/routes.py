"""Live classroom routes."""

from __future__ import annotations

from flask import (
    Blueprint, flash, jsonify, redirect, render_template, request,
    url_for,
)
from flask_login import current_user, login_required

from app.live import services

live_bp = Blueprint("live", __name__)


def _register_live_csrf_exempt(app):
    try:
        from app.extensions import csrf
        csrf.exempt(live_bp)
    except Exception:
        pass


# ── Student pages ──
@live_bp.route("/classes")
def class_list():
    classes = services.upcoming(limit=50)
    return render_template("live/index.html",
                           classes=classes, user=current_user)


@live_bp.route("/classes/<slug>")
@login_required
def class_detail(slug: str):
    lc = services.get_by_slug(slug)
    if lc is None:
        flash("Class not found.", "error")
        return redirect(url_for("live.class_list"))
    enrolled = services.is_enrolled(current_user.id, lc.id)
    show_url = enrolled and lc.status == "live"
    return render_template("live/detail.html",
                           lc=services.class_to_dict(lc, show_url),
                           lc_obj=lc, enrolled=enrolled,
                           user=current_user)


@live_bp.route("/classes/calendar")
@login_required
def class_calendar():
    events = services.calendar_events()
    return render_template("live/calendar.html",
                           events=events, user=current_user)


@live_bp.route("/classes/my")
@login_required
def my_classes():
    classes = services.enrolled_classes(current_user.id)
    return render_template("live/my_classes.html",
                           classes=classes, user=current_user)


# ── Registration ──
@live_bp.route("/classes/<slug>/register", methods=["POST"])
@login_required
def register(slug: str):
    lc = services.get_by_slug(slug)
    if lc is None:
        flash("Class not found.", "error")
        return redirect(url_for("live.class_list"))
    result = services.enroll(current_user.id, lc.id)
    from app.extensions import db
    db.session.commit()
    if result:
        flash(f"Registered for {lc.title}!", "success")
    else:
        flash("Could not register (class may be full).", "error")
    return redirect(url_for("live.class_detail", slug=slug))


@live_bp.route("/classes/<slug>/unregister", methods=["POST"])
@login_required
def unregister(slug: str):
    lc = services.get_by_slug(slug)
    if lc:
        services.unenroll(current_user.id, lc.id)
        from app.extensions import db
        db.session.commit()
        flash("Registration cancelled.", "success")
    return redirect(url_for("live.class_detail", slug=slug))


@live_bp.route("/classes/<slug>/join", methods=["POST"])
@login_required
def join_class(slug: str):
    lc = services.get_by_slug(slug)
    if lc is None or lc.status != "live":
        flash("Class is not live.", "error")
        return redirect(url_for("live.class_detail", slug=slug))
    if not services.is_enrolled(current_user.id, lc.id):
        flash("You must register first.", "error")
        return redirect(url_for("live.class_detail", slug=slug))
    services.mark_joined(current_user.id, lc.id)
    from app.extensions import db
    db.session.commit()
    return redirect(lc.meeting_url or
                    url_for("live.class_detail", slug=slug))


# ── Instructor ──
@live_bp.route("/instructor/classes")
@login_required
def instructor_dashboard():
    classes = LiveClass_query_by_instructor(current_user.id)
    return render_template("live/instructor.html",
                           classes=classes, user=current_user)


@live_bp.route("/instructor/classes/new", methods=["GET", "POST"])
@login_required
def create_class():
    if request.method == "POST":
        from app.extensions import db
        import re
        title = request.form.get("title", "").strip()
        slug = re.sub(r"[^a-z0-9-]", "",
                      title.lower().replace(" ", "-"))[:80]
        if not title:
            flash("Title required.", "error")
            return redirect(url_for("live.create_class"))
        services.create_class(
            current_user.id, title, slug,
            description=request.form.get("description", ""),
            category=request.form.get("category", "general"),
            difficulty=request.form.get("difficulty", "Easy"),
            capacity=int(request.form.get("capacity", 30)),
            status="scheduled")
        db.session.commit()
        flash(f"Class '{title}' created!", "success")
        return redirect(url_for("live.instructor_dashboard"))
    return render_template("live/create.html", user=current_user)


@live_bp.route("/instructor/classes/<int:class_id>/start",
               methods=["POST"])
@login_required
def start_class_route(class_id: int):
    lc = LiveClass_query_get(class_id)
    if lc is None or not lc.is_instructor(current_user):
        flash("Not authorized.", "error")
        return redirect(url_for("live.instructor_dashboard"))
    services.start_class(lc)
    from app.extensions import db
    db.session.commit()
    flash(f"Class '{lc.title}' is now LIVE!", "success")
    return redirect(url_for("live.instructor_dashboard"))


@live_bp.route("/instructor/classes/<int:class_id>/end",
               methods=["POST"])
@login_required
def end_class_route(class_id: int):
    lc = LiveClass_query_get(class_id)
    if lc is None or not lc.is_instructor(current_user):
        flash("Not authorized.", "error")
        return redirect(url_for("live.instructor_dashboard"))
    services.end_class(lc)
    from app.extensions import db
    db.session.commit()
    flash(f"Class '{lc.title}' ended.", "success")
    return redirect(url_for("live.instructor_dashboard"))


# ── API ──
@live_bp.route("/api/classes")
def api_classes():
    classes = services.upcoming(limit=50)
    return jsonify([services.class_to_dict(c) for c in classes])


@live_bp.route("/api/classes/calendar")
@login_required
def api_calendar():
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    return jsonify(services.calendar_events(month, year))


@live_bp.route("/api/classes/register", methods=["POST"])
@login_required
def api_register():
    data = request.get_json(silent=True) or {}
    class_id = int(data.get("class_id") or 0)
    if class_id <= 0:
        return jsonify({"error": "Missing class_id."}), 400
    result = services.enroll(current_user.id, class_id)
    from app.extensions import db
    db.session.commit()
    if result:
        return jsonify({"ok": True, "enrolled": True})
    return jsonify({"ok": False, "error": "Full or not found."}), 400


@live_bp.route("/api/classes/attendance", methods=["POST"])
@login_required
def api_attendance():
    data = request.get_json(silent=True) or {}
    class_id = int(data.get("class_id") or 0)
    action = data.get("action", "join")
    if class_id <= 0:
        return jsonify({"error": "Missing class_id."}), 400
    if action == "join":
        services.mark_joined(current_user.id, class_id)
    elif action == "leave":
        services.mark_left(current_user.id, class_id)
    from app.extensions import db
    db.session.commit()
    return jsonify({"ok": True})


# ── Helpers (avoid import issues) ──
def LiveClass_query_by_instructor(instructor_id: int):
    from app.live.models import LiveClass
    return LiveClass.query.filter_by(
        instructor_id=instructor_id).order_by(
        LiveClass.start_time.desc()).all()


def LiveClass_query_get(class_id: int):
    from app.live.models import LiveClass
    return LiveClass.query.get(class_id)


# ── Classroom experience ──
@live_bp.route("/classroom/<slug>")
@login_required
def classroom(slug: str):
    lc = services.get_by_slug(slug)
    if lc is None:
        flash("Class not found.", "error")
        return redirect(url_for("live.class_list"))
    enrolled = services.is_enrolled(current_user.id, lc.id)
    if not enrolled and lc.status == "live":
        flash("You must register first.", "error")
        return redirect(url_for("live.class_detail", slug=slug))
    show_url = enrolled and lc.status == "live"
    meeting_url = lc.meeting_url if show_url else ""
    # Build participant list.
    participants = []
    for e in (lc.enrollments or []):
        if e.user:
            icon = "🟢" if e.attendance_status == "present" else "⚪"
            participants.append({
                "username": e.user.username,
                "status_icon": icon,
            })
    return render_template("live/classroom.html",
                           lc=services.class_to_dict(lc, show_url),
                           lc_obj=lc, enrolled=enrolled,
                           meeting_url=meeting_url,
                           participants=participants,
                           user=current_user)


@live_bp.route("/instructor/classroom/<slug>")
@login_required
def instructor_classroom(slug: str):
    """Instructor view — same template with extra controls."""
    lc = services.get_by_slug(slug)
    if lc is None or not lc.is_instructor(current_user):
        flash("Not authorized.", "error")
        return redirect(url_for("live.instructor_dashboard"))
    meeting_url = lc.meeting_url or ""
    participants = []
    for e in (lc.enrollments or []):
        if e.user:
            icon = "🟢" if e.attendance_status == "present" else "⚪"
            participants.append({
                "username": e.user.username,
                "status_icon": icon,
            })
    return render_template("live/classroom.html",
                           lc=services.class_to_dict(lc, True),
                           lc_obj=lc, enrolled=True,
                           meeting_url=meeting_url,
                           participants=participants,
                           user=current_user)


@live_bp.route("/classes/<slug>/leave", methods=["GET", "POST"])
@login_required
def leave_class(slug: str):
    lc = services.get_by_slug(slug)
    if lc:
        services.mark_left(current_user.id, lc.id)
        from app.extensions import db
        db.session.commit()
    flash("You left the class. Attendance recorded.", "success")
    return redirect(url_for("live.my_classes"))
