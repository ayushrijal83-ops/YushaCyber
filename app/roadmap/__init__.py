"""Roadmap blueprint for YushaCyber.

Exposes ``roadmap_bp``, registered by the app factory under the
``/roadmap`` URL prefix. Routes live in ``routes.py``; importing them
here attaches them to the blueprint.
"""

from flask import Blueprint

roadmap_bp = Blueprint("roadmap", __name__)

from app.roadmap import routes  # noqa: E402,F401  (route registration)
