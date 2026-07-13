"""Admin package (YC-010.7).

Admin-only management interfaces. Access is gated by the existing
``User.is_admin`` flag — non-admins receive 403 Forbidden.
"""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__)

from app.admin import routes  # noqa: E402,F401  (attach routes)
