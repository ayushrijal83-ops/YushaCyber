"""Cyber Resources models.

    ResourceCategory 1 ──< Resource

Mirrors the conventions of the CTF and Labs modules: BaseModel for
id/created_at/updated_at, slugs unique and indexed, ordered child
collection with a delete-orphan cascade.

Read-only reference content — no authoring, uploads or user-generated data.
"""

from __future__ import annotations

from app.extensions import db
from app.models import BaseModel

# Same difficulty vocabulary used elsewhere in the platform.
RESOURCE_DIFFICULTIES = ("Beginner", "Intermediate", "Advanced")


class ResourceCategory(BaseModel):
    """A topic grouping in the knowledge library (e.g. Linux, OWASP)."""

    __tablename__ = "resource_categories"

    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=False, default="book")
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    resources = db.relationship(
        "Resource",
        back_populates="category",
        order_by="Resource.display_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<ResourceCategory {self.slug}>"


class Resource(BaseModel):
    """A single reference article in the library."""

    __tablename__ = "resources"

    category_id = db.Column(
        db.Integer, db.ForeignKey("resource_categories.id"),
        nullable=False, index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False, unique=True, index=True)
    summary = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=False, default="Beginner")
    estimated_read_minutes = db.Column(db.Integer, nullable=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False, index=True)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    category = db.relationship("ResourceCategory", back_populates="resources")

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<Resource {self.slug}>"
