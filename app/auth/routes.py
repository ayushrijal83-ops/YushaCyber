"""Authentication routes.

Controllers stay intentionally thin: they validate input via Flask-WTF
forms, delegate all business logic to ``services.py``, flash a result
and redirect. No database access happens directly in this module.
"""

from __future__ import annotations

from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import auth_bp, services
from app.auth.forms import ForgotPasswordForm, LoginForm, RegistrationForm


def _safe_next_url(default: str) -> str:
    """Return the ?next= target only if it is a local, relative URL.

    Prevents open-redirect attacks: any absolute URL pointing at another
    host is discarded in favour of the default.
    """
    target = request.args.get("next", "")
    if target and not urlparse(target).netloc and target.startswith("/"):
        return target
    return default


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a new account."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user, error = services.register_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
        )
        if error is not None:
            flash(error, "error")
        else:
            flash("Account created successfully! Please sign in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Sign in with username or email."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = services.authenticate_user(form.identifier.data, form.password.data)
        if user is None:
            # One uniform message — never reveal which part was wrong.
            flash("Invalid credentials. Check your details and try again.", "error")
        else:
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(_safe_next_url(default=url_for("dashboard.index")))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """End the session securely."""
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))


@auth_bp.route("/switch")
def switch_user():
    """Switch account (YC-023): end the current session and land on the
    sign-in page ready to accept a different account.

    Unlike plain ``logout``, this stashes the previous username in the
    session flash + a one-shot session key so the login form can show
    "Signed in as X? Continue as someone else." — making the difference
    visible to the user instead of behaving identically to logout.
    """
    from flask import session
    previous_name = None
    if current_user.is_authenticated:
        previous_name = current_user.username
    logout_user()
    if previous_name:
        session["_switch_from"] = previous_name
        flash(f"Signed out from {previous_name}. Sign in to a different account.",
              "success")
    else:
        flash("Sign in to continue.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Password recovery request.

    Email delivery is not wired up yet (no mail server in this task), so
    the route responds with the same neutral message whether or not the
    address exists — the standard anti-enumeration behaviour it will keep
    once sending is implemented.
    """
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        flash("If an account exists for that email, a reset link has been sent.",
              "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)
