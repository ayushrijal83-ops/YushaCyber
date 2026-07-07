"""Roadmap routes.

Thin controllers only — data assembly lives in ``services.py`` so the
placeholder tiers can be swapped for real roadmap content (YC-006.2+)
without touching this module.
"""

from __future__ import annotations

from flask import abort, render_template
from flask_login import current_user, login_required

from app.roadmap import roadmap_bp, services


@roadmap_bp.route("/")
@login_required
def index():
    """Render the roadmap page."""
    context = services.get_roadmap_context(current_user)
    return render_template("roadmap/roadmap.html", user=current_user, **context)


@roadmap_bp.route("/<module_slug>/")
@login_required
def module_detail(module_slug: str):
    """Render a single module and its lessons, or 404 if not found."""
    context = services.get_module_detail_context(current_user, module_slug)
    if context is None:
        abort(404)
    return render_template("roadmap/module.html", user=current_user, **context)
