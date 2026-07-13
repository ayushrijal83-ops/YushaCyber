"""Cyber Resources Hub package (YC-012.0).

A categorised knowledge library: models, service layer, seed, blueprint.
Not a blog or CMS — no editor, admin, comments, ratings, or uploads.
"""

from flask import Blueprint

resources_bp = Blueprint("resources", __name__)

from app.resources import routes  # noqa: E402,F401  (attach routes)
