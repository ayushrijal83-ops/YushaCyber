"""Public User Profiles feature (YC-023.0).

Standalone blueprint: showcases a user's learning journey at
``/users/<username>`` (public, read-only) and lets the account owner edit
their own profile at ``/profile``. Reuses every existing engine (XP,
achievements, certificates, labs, quizzes, CTF) via read-only queries —
none of those systems are modified.
"""

from __future__ import annotations

from flask import Blueprint

profiles_bp = Blueprint("profiles", __name__)

from app.profiles import routes  # noqa: E402,F401  (route registration)
