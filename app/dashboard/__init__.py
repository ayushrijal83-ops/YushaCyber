"""Dashboard blueprint for YushaCyber.

Exposes ``dashboard_bp``, registered by the app factory under the
``/dashboard`` URL prefix. Routes live in ``routes.py``; importing them
here attaches them to the blueprint.
"""

from flask import Blueprint

dashboard_bp = Blueprint("dashboard", __name__)

from app.dashboard import routes  # noqa: E402,F401  (route registration)
