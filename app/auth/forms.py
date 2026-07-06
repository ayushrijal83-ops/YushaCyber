"""Flask-WTF forms for registration, login and password recovery."""

from __future__ import annotations

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
    ValidationError,
)

from app.auth import services

# Password policy: 8+ chars with lowercase, uppercase and a digit.
PASSWORD_PATTERNS = (
    (re.compile(r"[a-z]"), "a lowercase letter"),
    (re.compile(r"[A-Z]"), "an uppercase letter"),
    (re.compile(r"\d"), "a number"),
)


def _validate_password_strength(_form: FlaskForm, field: PasswordField) -> None:
    """Reject weak passwords with a message listing what's missing."""
    missing = [label for pattern, label in PASSWORD_PATTERNS
               if not pattern.search(field.data or "")]
    if missing:
        raise ValidationError("Password must contain " + ", ".join(missing) + ".")


class RegistrationForm(FlaskForm):
    """New account form with strength + duplicate validation."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=30, message="Username must be 3–30 characters."),
            Regexp(
                r"^[A-Za-z0-9_]+$",
                message="Only letters, numbers and underscores are allowed.",
            ),
        ],
    )
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Enter a valid email address."),
            Length(max=255),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, max=128, message="Password must be at least 8 characters."),
            _validate_password_strength,
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords do not match."),
        ],
    )
    submit = SubmitField("Create Account")

    # WTForms calls validate_<field> hooks automatically.
    def validate_username(self, field: StringField) -> None:
        """Duplicate username detection."""
        if services.username_taken(field.data):
            raise ValidationError("That username is already taken.")

    def validate_email(self, field: StringField) -> None:
        """Duplicate email detection."""
        if services.email_taken(field.data):
            raise ValidationError("An account with that email already exists.")


class LoginForm(FlaskForm):
    """Sign-in form accepting username OR email."""

    identifier = StringField(
        "Username or email",
        validators=[
            DataRequired(message="Enter your username or email."),
            Length(max=255),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")],
    )
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")


class ForgotPasswordForm(FlaskForm):
    """Password recovery request form."""

    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Enter a valid email address."),
            Length(max=255),
        ],
    )
    submit = SubmitField("Send reset link")
