"""Global Leaderboards (YC-024.0).

Read-only rankings over the existing progress tables — auth, XP,
achievements, certificates, labs and CTF engines are all untouched.
"""

from __future__ import annotations

from flask import Blueprint

leaderboard_bp = Blueprint("leaderboard", __name__)

from app.leaderboard import routes  # noqa: E402,F401  (route registration)
