"""Database models for the authentication feature."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp (avoids the deprecated utcnow)."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """A YushaCyber account.

    Carries the gamification fields (xp, level, streak) that future
    features — dashboard, leaderboards, daily challenges, CTF progress —
    will build upon.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    profile_image = db.Column(db.String(255), nullable=False, default="default.png")
    bio = db.Column(db.Text, nullable=False, default="")

    xp = db.Column(db.Integer, nullable=False, default=0)
    level = db.Column(db.Integer, nullable=False, default=1)
    streak = db.Column(db.Integer, nullable=False, default=0)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    # ------------------------------------------------------------------
    # Password handling — plain-text passwords are never stored.
    # ------------------------------------------------------------------
    def set_password(self, password: str) -> None:
        """Hash and store the given password (scrypt via Werkzeug)."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the given password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Flask-Login callback: fetch a user by session-stored id."""
    return db.session.get(User, int(user_id))
