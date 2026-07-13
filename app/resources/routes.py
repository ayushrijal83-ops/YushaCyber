"""Cyber Resources routes.

Thin controllers only — all queries live in ``resource_services.py``.
"""

from __future__ import annotations

from flask import abort, render_template, request
from flask_login import current_user, login_required

from app.resources import resource_services, resources_bp


@resources_bp.route("/")
@login_required
def index():
    """Resources hub: categories, featured, popular, and search results."""
    context = resource_services.get_hub_context(request.args.get("q", ""))
    return render_template("resources/index.html", user=current_user, **context)


@resources_bp.route("/<category_slug>/")
@login_required
def category(category_slug: str):
    """All resources in a category."""
    context = resource_services.get_category_context(category_slug)
    if context is None:
        abort(404)
    return render_template("resources/category.html", user=current_user, **context)


@resources_bp.route("/<category_slug>/<resource_slug>/")
@login_required
def resource(category_slug: str, resource_slug: str):
    """A single reference article."""
    context = resource_services.get_resource_context(category_slug, resource_slug)
    if context is None:
        abort(404)
    return render_template("resources/detail.html", user=current_user, **context)
