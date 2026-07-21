"""Cloud lab models (YC-032.0).

One table: admin-created scenario accounts. Built-in accounts stay in
code (accounts.py); customs live here as validated JSON and shadow the
builtins by key — the same data-over-code philosophy as AD custom
domains.
"""

from __future__ import annotations

import json

from app.extensions import db
from app.models.base import BaseModel


class CloudCustomScenario(BaseModel):
    """An admin-authored virtual cloud account definition."""

    __tablename__ = "cloud_custom_scenarios"

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
        return f"<CloudCustomScenario {self.key}>"
