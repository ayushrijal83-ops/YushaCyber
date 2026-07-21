"""Active Directory lab models (YC-031.0).

One table: admin-created domain definitions. Built-in domains stay in
code (domains.py); customs live here as validated JSON — the same
data-over-code philosophy as topologies, with a DB home because admins
create them at runtime (file writes don't survive containerised
deploys).
"""

from __future__ import annotations

import json

from app.extensions import db
from app.models.base import BaseModel


class ADCustomDomain(BaseModel):
    """An admin-authored virtual domain definition."""

    __tablename__ = "ad_custom_domains"

    key = db.Column(db.String(64), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    definition_json = db.Column(db.Text, nullable=False, default="{}")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def get_definition(self) -> dict:
        try:
            data = json.loads(self.definition_json or "{}")
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def set_definition(self, definition: dict) -> None:
        self.definition_json = json.dumps(definition, indent=2)

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<ADCustomDomain {self.key}>"
