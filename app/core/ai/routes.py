"""AI API routes — /api/ai/chat, /api/ai/health, /api/ai/models."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


def _register_csrf_exempt(app):
    """Call after app.register_blueprint to exempt API from CSRF."""
    try:
        from app.extensions import csrf
        csrf.exempt(ai_bp)
    except Exception:
        pass


@ai_bp.route("/chat", methods=["POST"])
@login_required
def chat_endpoint():
    """POST /api/ai/chat — send a message to CyberMentor."""
    from app.core.ai.services import chat
    data = request.get_json(silent=True) or {}
    question = str(data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "Empty message."}), 400
    if len(question) > 2000:
        return jsonify({"error": "Message too long (max 2000)."}), 400
    current_lab = str(data.get("current_lab") or "")
    result = chat(current_user.id, question,
                  user=current_user, current_lab=current_lab)
    return jsonify(result)


@ai_bp.route("/health")
def health_endpoint():
    """GET /api/ai/health — provider health check."""
    from app.core.ai.services import health
    return jsonify(health())


@ai_bp.route("/models")
def models_endpoint():
    """GET /api/ai/models — list available models."""
    from app.core.ai.services import models
    return jsonify({"models": models()})


@ai_bp.route("/context")
@login_required
def context_endpoint():
    """GET /api/ai/context — debug: show current context (admin only)."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Admin only."}), 403
    from app.core.ai.context_engine import get_context_dict, filter_for_ai
    ctx = get_context_dict(current_user)
    return jsonify(filter_for_ai(ctx))


@ai_bp.route("/hint", methods=["POST"])
@login_required
def hint_endpoint():
    """POST /api/ai/hint — request a smart hint."""
    from app.core.ai.hints import get_hint
    data = request.get_json(silent=True) or {}
    objective_id = int(data.get("objective_id") or 0)
    if objective_id <= 0:
        return jsonify({"error": "Missing objective_id."}), 400
    is_admin = getattr(current_user, "is_admin", False)
    response = get_hint(current_user.id, objective_id, is_admin)
    return jsonify(response.to_dict())


@ai_bp.route("/recommendations")
@login_required
def recommendations_endpoint():
    """GET /api/ai/recommendations — personalized learning recs."""
    from app.core.ai.recommendations import get_recommendations
    recs = get_recommendations(current_user, limit=5)
    return jsonify({"recommendations": [r.to_dict() for r in recs]})


@ai_bp.route("/skill-profile")
@login_required
def skill_profile_endpoint():
    """GET /api/ai/skill-profile — student skill analysis."""
    from app.core.ai.recommendations import get_skill_profile
    return jsonify(get_skill_profile(current_user).to_dict())


# ------------------------------------------------------------------
# AI Analytics API (admin only)
# ------------------------------------------------------------------
@ai_bp.route("/admin/analytics")
@login_required
def analytics_endpoint():
    """GET /api/ai/admin/analytics — dashboard metrics (admin only)."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Admin only."}), 403
    from app.core.ai.analytics import dashboard_dict
    return jsonify(dashboard_dict())


@ai_bp.route("/admin/report")
@login_required
def report_endpoint():
    """GET /api/ai/admin/report?period=daily — generate report."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Admin only."}), 403
    period = request.args.get("period", "daily")
    from app.core.ai.analytics import get_report
    return jsonify(get_report(period))


@ai_bp.route("/admin/export")
@login_required
def export_endpoint():
    """GET /api/ai/admin/export?dataset=all&format=json."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Admin only."}), 403
    dataset = request.args.get("dataset", "all")
    fmt = request.args.get("format", "json")
    from app.core.ai.analytics import export_data
    data = export_data(dataset, fmt)
    if fmt == "csv":
        return data, 200, {"Content-Type": "text/csv",
                            "Content-Disposition": f"attachment; filename={dataset}.csv"}
    return data, 200, {"Content-Type": "application/json"}


@ai_bp.route("/admin/charts")
@login_required
def charts_endpoint():
    """GET /api/ai/admin/charts — chart data series."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Admin only."}), 403
    from app.core.ai.analytics import get_charts
    return jsonify({"charts": get_charts()})
