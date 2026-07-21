"""Learning-analytics models (YC-033.0).

One table: a generic, append-only event stream owned by the analytics
module. Nothing else writes here, and nothing here alters existing
systems — features that were never instrumented (e.g. lab hint usage)
start producing data the moment the tracker ships, without touching
the Lab Engine.
"""

from __future__ import annotations

import json

from app.extensions import db
from app.models.base import BaseModel

#: Event types the /events endpoint accepts. A whitelist, not a hint —
#: anything else is rejected with 400.
TRACKED_EVENT_TYPES = ("hint_used",)


class AnalyticsEvent(BaseModel):
    """A single analytics fact: who did what to which subject, when.

    ``created_at`` (from BaseModel) is the event timestamp.
    """

    __tablename__ = "analytics_events"

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    event_type = db.Column(db.String(40), nullable=False, index=True)
    #: What the event is about, e.g. subject_type="objective",
    #: subject_id=<LabObjective.id>.
    subject_type = db.Column(db.String(40), nullable=False, default="")
    subject_id = db.Column(db.Integer, nullable=True)
    #: Small JSON payload for context (e.g. {"lab": "cloud-open-ssh"}).
    meta_json = db.Column(db.Text, nullable=False, default="{}")

    def get_meta(self) -> dict:
        try:
            data = json.loads(self.meta_json or "{}")
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def set_meta(self, meta: dict) -> None:
        self.meta_json = json.dumps(meta or {})

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<AnalyticsEvent {self.event_type} u{self.user_id}>"
