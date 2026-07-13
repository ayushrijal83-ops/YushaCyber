"""Cyber Labs routes.

Thin controllers ONLY. Every route delegates to lab_services and returns
plain data. No route knows which simulator drives a lab — that is the whole
point of the engine. Adding Nmap/Wireshark/Burp requires ZERO route changes.
"""

from __future__ import annotations

from flask import abort, jsonify, render_template, request
from flask_login import current_user, login_required

from app.labs import labs_bp, lab_services


@labs_bp.route("/")
@login_required
def index():
    """Labs catalogue."""
    return render_template(
        "labs/index.html",
        user=current_user,
        categories=lab_services.get_categories(),
        labs=lab_services.get_labs(),
    )


@labs_bp.route("/<slug>")
@login_required
def detail(slug: str):
    """A lab: interactive workspace when it has a simulator, else read-only."""
    lab = lab_services.get_lab(slug)
    if lab is None:
        abort(404)

    context = {}
    if lab.is_interactive:
        context = lab_services.get_workspace_context(current_user, lab)

    return render_template(
        "labs/detail.html", user=current_user, lab=lab, **context
    )


@labs_bp.route("/<slug>/action", methods=["POST"])
@login_required
def action(slug: str):
    """Run one action against the lab's simulator (JSON in, JSON out).

    Capability-agnostic: `type` may be "command" today, "select"/"flag"/
    "submit" for future inspector, packet-viewer, browser or editor labs —
    the route does not change.
    """
    lab = lab_services.get_lab(slug)
    if lab is None:
        abort(404)

    data = request.get_json(silent=True) or {}
    action_type = str(data.get("type") or "command")
    payload = data.get("payload") or {}

    result = lab_services.execute_action(current_user, lab, action_type, payload)
    if not result.get("ok"):
        return jsonify(result), 400
    return jsonify(result)


@labs_bp.route("/<slug>/reset", methods=["POST"])
@login_required
def reset(slug: str):
    """Reset the simulated session state (objective/XP history is kept)."""
    lab = lab_services.get_lab(slug)
    if lab is None:
        abort(404)
    result = lab_services.reset_lab_session(current_user, lab)
    return jsonify(result), (200 if result.get("ok") else 400)
