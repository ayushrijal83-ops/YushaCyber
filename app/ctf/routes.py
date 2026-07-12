"""CTF routes.

Thin controllers only — data assembly lives in ``services.py`` so the
templates never touch the ORM.
"""

from __future__ import annotations

from flask import render_template
from flask_login import current_user, login_required

from app.ctf import ctf_bp, services


@ctf_bp.route("/")
@login_required
def index():
    """Render the CTF challenge browser (auth-only)."""
    context = services.get_ctf_page_context(current_user)
    return render_template("ctf/index.html", user=current_user, **context)
