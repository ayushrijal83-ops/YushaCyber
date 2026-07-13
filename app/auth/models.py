"""Database models for the authentication feature.

The User model is the foundation for every account-based feature on the
platform: dashboard, learning progress, XP, profiles, leaderboards,
certificates, daily challenges and CTF progress.

Portability note: only standard SQLAlchemy column types are used
(Integer, String, Text, Boolean, DateTime) so the model runs unchanged
on SQLite in development and PostgreSQL in production.
"""

from __future__ import annotations

from typing import Optional

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.models import BaseModel


class User(BaseModel, UserMixin):
    """A YushaCyber account.

    Security invariants:
    - ``password_hash`` only ever holds a Werkzeug hash; plain-text
      passwords are hashed in :meth:`set_password` and never persisted.
    - The hash is excluded from ``__repr__`` and must never be serialised
      or returned by any API built on this model.
    """

    __tablename__ = "users"

    # id, created_at and updated_at are inherited from BaseModel.

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------
    profile_image = db.Column(
        db.String(255),
        nullable=False,
        default="default.png",
    )
    bio = db.Column(db.Text, nullable=True)  # optional short biography

    # ------------------------------------------------------------------
    # Gamification — consumed by dashboard, leaderboards, challenges.
    # ------------------------------------------------------------------
    xp = db.Column(db.Integer, nullable=False, default=0)
    level = db.Column(db.Integer, nullable=False, default=1)
    streak = db.Column(db.Integer, nullable=False, default=0)

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------
    # Coarse role for future permission tiers: student | mentor | admin.
    # Indexed because role-filtered queries (e.g. mentor lists) are
    # expected once those features land.
    role = db.Column(db.String(20), nullable=False, default="student", index=True)

    # ------------------------------------------------------------------
    # Account state
    # ------------------------------------------------------------------
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    # Overrides UserMixin.is_active: Flask-Login refuses login_user() for
    # inactive accounts, giving us a ban/deactivation switch for free.
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # ------------------------------------------------------------------
    # Password handling — plain-text passwords are never stored.
    # ------------------------------------------------------------------
    def set_password(self, password: str) -> None:
        """Hash the given password (Werkzeug, scrypt) and store the hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the given password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        # Spec format "<User username>"; deliberately excludes email and
        # password_hash so reprs are always safe to log.
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Flask-Login callback: fetch a user by the id stored in the session.

    Returns None for unknown or malformed ids, which Flask-Login treats
    as an anonymous session rather than an error.
    """
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
