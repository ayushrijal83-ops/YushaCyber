"""Business logic for authentication.

Routes stay thin: every database interaction and authentication decision
lives here. Database errors are caught and logged; callers receive a
clean result and users never see internals or stack traces.
"""

from __future__ import annotations

from typing import Optional

from flask import current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from extensions import db


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def get_user_by_email(email: str) -> Optional[User]:
    """Return the user with this email (case-insensitive), or None."""
    normalized = email.strip().lower()
    return User.query.filter(func.lower(User.email) == normalized).first()


def get_user_by_username(username: str) -> Optional[User]:
    """Return the user with this username (case-insensitive), or None."""
    normalized = username.strip().lower()
    return User.query.filter(func.lower(User.username) == normalized).first()


def get_user_by_identifier(identifier: str) -> Optional[User]:
    """Resolve a login identifier that may be a username OR an email."""
    if "@" in identifier:
        return get_user_by_email(identifier)
    return get_user_by_username(identifier)


# ---------------------------------------------------------------------------
# Duplicate detection (used by form validators)
# ---------------------------------------------------------------------------
def username_taken(username: str) -> bool:
    """True if the username is already registered."""
    return get_user_by_username(username) is not None


def email_taken(email: str) -> bool:
    """True if the email is already registered."""
    return get_user_by_email(email) is not None


# ---------------------------------------------------------------------------
# Account creation
# ---------------------------------------------------------------------------
def create_user(username: str, email: str, password: str) -> Optional[User]:
    """Create a new account with a hashed password.

    Returns the new User on success, or None if persistence failed.
    The plain-text password is hashed immediately and never stored.
    """
    user = User(username=username.strip(), email=email.strip().lower())
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        return user
    except SQLAlchemyError:
        # Roll back and log internally; never expose database errors.
        db.session.rollback()
        current_app.logger.exception("Failed to create user %r", username)
        return None


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def check_password(user: User, password: str) -> bool:
    """Verify a password against a user's stored hash."""
    return user.check_password(password)


def authenticate_user(identifier: str, password: str) -> Optional[User]:
    """Return the user if identifier + password are valid, else None.

    A single code path for "unknown user" and "wrong password" keeps the
    response time and error message uniform, avoiding account enumeration.
    """
    user = get_user_by_identifier(identifier)
    if user is not None and check_password(user, password):
        return user
    return None
