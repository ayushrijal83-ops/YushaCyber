"""Dashboard routes.

Thin controllers only — all data assembly lives in ``services.py`` so the
placeholder values can be swapped for real database queries (XP events,
course progress, achievements) without touching this module.
"""

from __future__ import annotations

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.dashboard import dashboard_bp, services


@dashboard_bp.route("/")
@login_required
def index():
    """Render the authenticated user dashboard."""
    context = services.get_dashboard_context(current_user)
    return render_template("dashboard/dashboard.html", user=current_user, **context)


@dashboard_bp.route("/achievements")
@login_required
def achievements():
    """Render the achievements page (auth-only)."""
    from app.achievement.services import get_achievements_page_context

    context = get_achievements_page_context(current_user)
    return render_template(
        "dashboard/achievements.html", user=current_user, **context
    )


@dashboard_bp.route("/certificates")
@login_required
def certificates():
    """Render the My Certificates page (auth-only)."""
    from app.certificates.services import get_certificates_page_context

    context = get_certificates_page_context(current_user)
    return render_template(
        "dashboard/certificates.html", user=current_user, **context
    )


# ===========================================================================
# REMOVE BEFORE PRODUCTION — development-only XP testing route.
#
# Lets developers exercise the XP/Level engine without waiting for lessons
# or challenges to exist: /dashboard/test-xp/50 awards 50 XP and returns
# to the dashboard. Delete this entire block (and its test) before deploy.
# ===========================================================================
@dashboard_bp.route("/test-xp/<int:amount>")
@login_required
def test_xp(amount: int):
    """DEV ONLY: award ``amount`` XP to the current user and redirect back."""
    previous_level = current_user.level
    services.award_xp(current_user, amount)
    if current_user.level > previous_level:
        flash(f"+{amount} XP — LEVEL UP! You reached Level {current_user.level}.",
              "success")
    else:
        flash(f"+{amount} XP awarded.", "success")
    return redirect(url_for("dashboard.index"))
