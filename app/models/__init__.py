"""Shared model infrastructure for YushaCyber.

Feature-specific models live with their features (e.g. the User model in
``app/auth/models.py``); this package holds what they have in common.

Usage::

    from app.models import BaseModel

    class Course(BaseModel):
        __tablename__ = "courses"
        title = db.Column(db.String(120), nullable=False)
"""

from app.models.base import BaseModel, utcnow

__all__ = ["BaseModel", "utcnow"]
