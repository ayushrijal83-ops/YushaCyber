"""Abstract base model shared by every table in YushaCyber.

Any concrete model should inherit from :class:`BaseModel` instead of
``db.Model`` directly, so the primary key and audit timestamps are
defined exactly once across the whole schema.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp (avoids the deprecated ``utcnow``)."""
    return datetime.now(timezone.utc)


class BaseModel(db.Model):
    """Abstract foundation: surrogate key + created/updated audit columns.

    ``__abstract__`` prevents SQLAlchemy from creating a table for this
    class itself; only subclasses become tables.
    """

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)

    # Set once when the row is inserted.
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    # Refreshed automatically on every UPDATE.
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
