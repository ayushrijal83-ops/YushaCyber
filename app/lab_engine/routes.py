"""Lab engine routes — API for interactive browser labs."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.lab_engine import services

lab_engine_bp = Blueprint("lab_engine", __name__,
                          url_prefix="/api/lab-engine")


@lab_engine_bp.route("/labs")
def api_labs():
    """GET /api/lab-engine/labs — list available interactive labs."""
    return jsonify(services.available_labs())


@lab_engine_bp.route("/start", methods=["POST"])
@login_required
def api_start():
    """POST /api/lab-engine/start — start or resume a lab."""
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug") or "").strip()
    if not slug:
        return jsonify({"error": "Missing slug."}), 400
    result = services.start_lab(current_user.id, slug)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@lab_engine_bp.route("/execute", methods=["POST"])
@login_required
def api_execute():
    """POST /api/lab-engine/execute — run a terminal command."""
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug") or "")
    command = str(data.get("command") or "").strip()
    if not slug or not command:
        return jsonify({"error": "Missing slug or command."}), 400
    if len(command) > 500:
        return jsonify({"error": "Command too long."}), 400
    return jsonify(services.execute_command(
        current_user.id, slug, command))


@lab_engine_bp.route("/answer", methods=["POST"])
@login_required
def api_answer():
    """POST /api/lab-engine/answer — submit a text answer."""
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug") or "")
    obj_id = str(data.get("objective_id") or "")
    answer = str(data.get("answer") or "")
    if not slug or not obj_id:
        return jsonify({"error": "Missing slug or objective_id."}), 400
    return jsonify(services.submit_answer(
        current_user.id, slug, obj_id, answer))


@lab_engine_bp.route("/reset", methods=["POST"])
@login_required
def api_reset():
    """POST /api/lab-engine/reset — reset a lab."""
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug") or "")
    if not slug:
        return jsonify({"error": "Missing slug."}), 400
    return jsonify(services.reset_lab(current_user.id, slug))


@lab_engine_bp.route("/session/<slug>")
@login_required
def api_session(slug: str):
    """GET /api/lab-engine/session/<slug> — current session state."""
    result = services.get_session(current_user.id, slug)
    if result is None:
        return jsonify({"error": "No active session."}), 404
    return jsonify(result)


def _register_csrf_exempt(app):
    try:
        from app.extensions import csrf
        csrf.exempt(lab_engine_bp)
    except (ImportError, RuntimeError):
        pass
