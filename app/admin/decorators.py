"""Admin access control.

Reuses the existing ``User.is_admin`` flag on the auth model — no new
role system. Non-admin (or anonymous) users receive 403 Forbidden.
"""

from __future__ import annotations

from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(view):
    """Allow only authenticated administrators; otherwise abort 403."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view(*args, **kwargs)

    return wrapped
