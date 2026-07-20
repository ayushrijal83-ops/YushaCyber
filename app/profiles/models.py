"""Profile model (YC-023.0).

A separate one-to-one table so the existing ``users`` table — and all of
the authentication code that owns it — stays completely untouched.
"""

from __future__ import annotations

from app.models.base import BaseModel
from app.extensions import db


class UserProfile(BaseModel):
    """Public-profile fields a user can edit about themselves."""

    __tablename__ = "user_profiles"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    bio = db.Column(db.String(500), nullable=True)
    country = db.Column(db.String(56), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    website_url = db.Column(db.String(255), nullable=True)

    # Attached from this side (backref) so the auth model file is not edited:
    #   some_user.public_profile -> UserProfile | None
    user = db.relationship(
        "User",
        backref=db.backref("public_profile", uselist=False),
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<UserProfile user={self.user_id}>"
