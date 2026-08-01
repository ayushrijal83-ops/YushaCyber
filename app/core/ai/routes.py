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
