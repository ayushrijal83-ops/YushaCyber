"""CTF routes.

Thin controllers only — data assembly lives in ``services.py`` so the
templates never touch the ORM.
"""

from __future__ import annotations

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.ctf import ctf_bp, services


@ctf_bp.route("/")
@login_required
def index():
    """Render the CTF challenge browser (auth-only)."""
    context = services.get_ctf_page_context(current_user)
    return render_template("ctf/index.html", user=current_user, **context)


@ctf_bp.route("/<category_slug>/<challenge_slug>/", methods=["GET"])
@login_required
def challenge_detail(category_slug: str, challenge_slug: str):
    """Render a challenge's detail page, or 404 if it doesn't exist."""
    context = services.get_challenge_page_context(
        current_user, category_slug, challenge_slug
    )
    if context is None:
        abort(404)
    return render_template("ctf/challenge.html", user=current_user, **context)


@ctf_bp.route("/<category_slug>/<challenge_slug>/", methods=["POST"])
@login_required
def challenge_submit(category_slug: str, challenge_slug: str):
    """Handle a flag submission (POST, CSRF), then redirect back."""
    challenge = services.get_challenge(challenge_slug)
    if challenge is None:
        abort(404)

    # Already solved: don't record further attempts.
    if services.has_solved(current_user, challenge):
        flash("You've already solved this challenge.", "success")
        return redirect(url_for(
            "ctf.challenge_detail",
            category_slug=category_slug, challenge_slug=challenge_slug,
        ))

    submitted = (request.form.get("flag") or "").strip()
    result = services.submit_flag(current_user, challenge, submitted)

    if result.get("error"):
        flash("Unable to submit flag. Please try again.", "error")
    elif result["correct"]:
        flash("✅ Correct Flag — Challenge Solved!", "success")
    else:
        flash("❌ Incorrect Flag — Please try again.", "error")

    return redirect(url_for(
        "ctf.challenge_detail",
        category_slug=category_slug, challenge_slug=challenge_slug,
    ))
