"""Learning-analytics routes (YC-033.0).

Admin-only dashboard pages plus one login-required event endpoint (the
hint tracker). All numbers come precomputed from services — templates
only render.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    abort,
    jsonify,
    render_template,
    request,
)
from flask_login import current_user, login_required

from app.admin.decorators import admin_required
from app.analytics import export, services
from app.analytics.models import TRACKED_EVENT_TYPES
from app.auth.models import User

analytics_bp = Blueprint("analytics", __name__)


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Dashboard pages
# ---------------------------------------------------------------------------
@analytics_bp.route("/")
@admin_required
def overview():
    return render_template(
        "analytics/overview.html",
        stats=services.overview_stats(),
        series=services.timeseries(days=30),
    )


@analytics_bp.route("/students")
@admin_required
def students():
    q = request.args.get("q", "")
    level = _int_or_none(request.args.get("level"))
    min_xp = _int_or_none(request.args.get("min_xp"))
    sort = request.args.get("sort", "xp")
    results = services.search_students(q=q, level=level, min_xp=min_xp,
                                       sort=sort)
    return render_template("analytics/students.html", students=results,
                           q=q, level=level, min_xp=min_xp, sort=sort)


@analytics_bp.route("/students/<int:user_id>")
@admin_required
def student_detail(user_id: int):
    user = User.query.get_or_404(user_id)
    return render_template("analytics/student_detail.html", student=user,
                           data=services.student_analytics(user))


@analytics_bp.route("/content")
@admin_required
def content():
    return render_template(
        "analytics/content.html",
        roadmaps=services.roadmap_analytics(),
        labs=services.lab_analytics(),
        ctf=services.ctf_analytics(),
    )


# ---------------------------------------------------------------------------
# Exports — CSV now; PDF plugs into the same payload builders later.
# ---------------------------------------------------------------------------
@analytics_bp.route("/export/<report>.csv")
@admin_required
def export_csv(report: str):
    if report == "students":
        results = services.search_students(
            q=request.args.get("q", ""),
            level=_int_or_none(request.args.get("level")),
            min_xp=_int_or_none(request.args.get("min_xp")),
            sort=request.args.get("sort", "xp"))
        payload = export.students_payload(results)
    else:
        builder = export.PAYLOADS.get(report)
        if builder is None:
            abort(404)
        payload = builder()
    return Response(
        export.to_csv(payload),
        mimetype="text/csv",
        headers={"Content-Disposition":
                 f"attachment; filename=yushacyber-{report}.csv"})


@analytics_bp.route("/export/<report>.pdf")
@admin_required
def export_pdf(report: str):
    """Future-ready: the payload builders already exist; a PDF renderer
    slots in here without touching any analytics logic."""
    if report != "students" and report not in export.PAYLOADS:
        abort(404)
    return jsonify({
        "status": "not_implemented",
        "message": "PDF export is planned — use the CSV export for now. "
                   "The report payloads are already PDF-ready.",
    }), 501


# ---------------------------------------------------------------------------
# Event tracking (students) — the hint-usage instrument.
# ---------------------------------------------------------------------------
@analytics_bp.route("/events", methods=["POST"])
@login_required
def track_event():
    data = request.get_json(silent=True) or {}
    event_type = str(data.get("event_type", ""))
    if event_type not in TRACKED_EVENT_TYPES:
        return jsonify({"ok": False, "error": "unknown event type"}), 400
    subject_id = _int_or_none(str(data.get("subject_id", "")))
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    services.record_event(
        user_id=current_user.id,
        event_type=event_type,
        subject_type=str(data.get("subject_type", ""))[:40],
        subject_id=subject_id,
        meta={k: str(v)[:120] for k, v in list(meta.items())[:8]},
    )
    return jsonify({"ok": True})
