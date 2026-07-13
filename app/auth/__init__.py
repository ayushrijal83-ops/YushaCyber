"""Authentication blueprint for YushaCyber.

Exposes ``auth_bp``, registered by the app factory under the ``/auth``
URL prefix. Routes live in ``routes.py``; importing them here attaches
them to the blueprint.
"""

from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

from app.auth import routes  # noqa: E402,F401  (route registration)
