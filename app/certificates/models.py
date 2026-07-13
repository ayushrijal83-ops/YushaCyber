"""Certificate models.

    Certificate 1 ──< UserCertificate >── 1 User

A ``Certificate`` is a definition (title, unlock requirements, type). A
``UserCertificate`` records that a specific user has earned one, carrying
a unique human-readable ``certificate_code`` and a unique
(user_id, certificate_id) constraint so a certificate is issued at most
once per user. Both inherit id/created_at/updated_at from BaseModel. The
User relationship is attached via backref so the auth model file stays
untouched.

This foundation ticket defines schema only — no issuing logic lives here.
"""

from __future__ import annotations

from app.extensions import db
from app.models import BaseModel


class Certificate(BaseModel):
    """A single certificate definition."""

    __tablename__ = "certificates"

    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default="general")
    icon = db.Column(db.String(50), nullable=False, default="award")

    # Grouping/type label, e.g. "course", "track", "special".
    certificate_type = db.Column(db.String(50), nullable=False, default="course")

    # Requirements consumed by the (future) issuing engine. Module/quiz
    # requirements are stored as comma-separated slugs; xp as an integer.
    required_modules = db.Column(db.Text, nullable=True)
    required_quizzes = db.Column(db.Text, nullable=True)
    required_xp = db.Column(db.Integer, nullable=False, default=0)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)

    # One certificate -> many per-user issued rows.
    user_certificates = db.relationship(
        "UserCertificate",
        back_populates="certificate",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<Certificate {self.slug}>"


class UserCertificate(BaseModel):
    """Records that a user has earned a certificate (once)."""

    __tablename__ = "user_certificates"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "certificate_id", name="uq_user_certificate"
        ),
    )

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    certificate_id = db.Column(
        db.Integer, db.ForeignKey("certificates.id"), nullable=False, index=True
    )
    # Unique human-readable code, e.g. "YC-2026-000001".
    certificate_code = db.Column(
        db.String(30), nullable=False, unique=True, index=True
    )
    issued_at = db.Column(db.DateTime(timezone=True), nullable=True)

    certificate = db.relationship(
        "Certificate", back_populates="user_certificates"
    )
    # Attached from this side so the User model file stays untouched:
    #   some_user.certificates -> query of UserCertificate rows
    user = db.relationship(
        "User",
        backref=db.backref("certificates", lazy="dynamic"),
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<UserCertificate user={self.user_id} code={self.certificate_code}>"
