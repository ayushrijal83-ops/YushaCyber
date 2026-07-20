"""Profile routes (YC-023.0).

Security model:
  · ``/users/<username>`` — public, read-only, GET only. 404 for unknown
    usernames. No email or private data is ever placed in the context.
  · ``/profile`` — the signed-in user's own profile (same read-only page,
    plus the Edit button).
  · ``/profile/edit`` — GET form / POST save, and it can only ever touch
    ``current_user``'s row: no user id or username is accepted from the
    request, so editing someone else's profile is structurally impossible.

Admins can view all profiles the same way everyone can — profiles are
public by design (GitHub/TryHackMe model).
"""

from __future__ import annotations

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.auth.models import User
from app.profiles import profiles_bp, services
from app.profiles.forms import EditProfileForm


@profiles_bp.route("/users/<username>")
def public_profile(username: str):
    """Public, read-only profile page for any user."""
    profile_user = User.query.filter_by(username=username).first()
    if profile_user is None:
        abort(404)
    viewer = current_user if current_user.is_authenticated else None
    context = services.get_profile_page_context(profile_user, viewer)
    return render_template("profiles/profile.html", **context)


@profiles_bp.route("/profile")
@login_required
def my_profile():
    """The signed-in user's own profile (adds the Edit button)."""
    context = services.get_profile_page_context(current_user, current_user)
    return render_template("profiles/profile.html", **context)


@profiles_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit the CURRENT user's profile — never anyone else's."""
    profile = services.get_or_create_profile(current_user)
    form = EditProfileForm(obj=profile)

    if form.validate_on_submit():
        services.update_profile(current_user, form)
        flash("Profile updated.", "success")
        return redirect(url_for("profiles.my_profile"))

    return render_template(
        "profiles/edit.html", form=form, user=current_user,
    )
