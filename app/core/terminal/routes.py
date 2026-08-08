"""Terminal routes — API endpoints + lab page."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.core.terminal import services

terminal_bp = Blueprint("terminal", __name__)


@terminal_bp.route("/terminal")
@terminal_bp.route("/terminal/<slug>")
@login_required
def terminal_page(slug: str = "linux-basics"):
    """Render the terminal lab page."""
    services.start_shell(current_user.id, slug)
    return render_template("labs/terminal.html",
                           lab_slug=slug, user=current_user)


@terminal_bp.route("/api/terminal/start", methods=["POST"])
@login_required
def api_start():
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug", "terminal"))
    result = services.start_shell(current_user.id, slug)
    return jsonify(result)


@terminal_bp.route("/api/terminal/execute", methods=["POST"])
@login_required
def api_execute():
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug", "terminal"))
    command = str(data.get("command", "")).strip()
    if not command:
        return jsonify({"error": "Empty command."}), 400
    if len(command) > 500:
        return jsonify({"error": "Command too long."}), 400
    return jsonify(services.execute(current_user.id, slug, command))


@terminal_bp.route("/api/terminal/complete", methods=["POST"])
@login_required
def api_complete():
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug", "terminal"))
    partial = str(data.get("partial", ""))
    return jsonify({"matches": services.complete(
        current_user.id, slug, partial)})


@terminal_bp.route("/api/terminal/reset", methods=["POST"])
@login_required
def api_reset():
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug", "terminal"))
    return jsonify(services.reset_shell(current_user.id, slug))


@terminal_bp.route("/api/terminal/context")
@login_required
def api_context():
    slug = request.args.get("slug", "terminal")
    return jsonify(services.shell_context(current_user.id, slug))


def _register_csrf_exempt(app):
    try:
        from app.extensions import csrf
        csrf.exempt(terminal_bp)
    except (ImportError, RuntimeError):
        pass


# ══════════════════════════════════════════════
# Mission API (YC-034.2)
# ══════════════════════════════════════════════
@terminal_bp.route("/terminal/mission/<slug>")
@login_required
def mission_page(slug: str):
    """Render the mission terminal page."""
    from app.core.missions import start_mission
    data = start_mission(current_user.id, slug)
    if "error" in data:
        from flask import flash, redirect, url_for
        flash(data["error"], "error")
        return redirect(url_for("terminal.terminal_page"))
    return render_template("labs/terminal.html",
                           lab_slug=slug, mission=data,
                           user=current_user, current_lab=slug)


@terminal_bp.route("/api/terminal/mission/start", methods=["POST"])
@login_required
def api_mission_start():
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug", ""))
    if not slug:
        return jsonify({"error": "Missing slug."}), 400
    from app.core.missions import start_mission
    return jsonify(start_mission(current_user.id, slug))


@terminal_bp.route("/api/terminal/mission/execute", methods=["POST"])
@login_required
def api_mission_execute():
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug", ""))
    command = str(data.get("command", "")).strip()
    if not slug or not command:
        return jsonify({"error": "Missing slug or command."}), 400
    from app.core.missions import execute_command
    return jsonify(execute_command(current_user.id, slug, command))


@terminal_bp.route("/api/terminal/mission/hint", methods=["POST"])
@login_required
def api_mission_hint():
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug", ""))
    obj_id = str(data.get("objective_id", ""))
    from app.core.missions import get_hint
    return jsonify(get_hint(current_user.id, slug, obj_id))


@terminal_bp.route("/api/terminal/mission/progress")
@login_required
def api_mission_progress():
    slug = request.args.get("slug", "")
    from app.core.missions import get_progress
    result = get_progress(current_user.id, slug)
    if result is None:
        return jsonify({"error": "No active mission."}), 404
    return jsonify(result)


@terminal_bp.route("/api/terminal/mission/reset", methods=["POST"])
@login_required
def api_mission_reset():
    data = request.get_json(silent=True) or {}
    slug = str(data.get("slug", ""))
    from app.core.missions import reset_mission
    return jsonify(reset_mission(current_user.id, slug))


@terminal_bp.route("/api/terminal/missions")
def api_missions_list():
    from app.core.missions import available_missions
    return jsonify(available_missions())
