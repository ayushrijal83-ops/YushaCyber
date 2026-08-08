"""Durable mission-progress ledger.

The mission engine itself (mission_runner/mission_services) keeps live
session state in memory for speed and simplicity. This model is a thin,
durable record of *where a student stands* on each mission — written
alongside that in-memory state — so the Interactive Missions UI can show
accurate status (locked / available / in progress / completed) and
aggregate stats (XP earned, missions completed) even across restarts,
without depending on an in-memory dict surviving.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.extensions import db
from app.models.base import BaseModel

STATUS_AVAILABLE = "available"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


class MissionRecord(BaseModel):
    """One row per (user, mission) — the durable progress summary."""

    __tablename__ = "mission_records"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    mission_id = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default=STATUS_IN_PROGRESS)
    objectives_completed = db.Column(db.Integer, nullable=False, default=0)
    objectives_total = db.Column(db.Integer, nullable=False, default=0)
    xp_earned = db.Column(db.Integer, nullable=False, default=0)
    hints_used = db.Column(db.Integer, nullable=False, default=0)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "mission_id", name="uq_mission_record_user_mission"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "status": self.status,
            "objectives_completed": self.objectives_completed,
            "objectives_total": self.objectives_total,
            "xp_earned": self.xp_earned,
            "hints_used": self.hints_used,
            "attempts": self.attempts,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


def get_record(user_id: int, mission_id: str) -> MissionRecord | None:
    return MissionRecord.query.filter_by(user_id=user_id, mission_id=mission_id).first()


def upsert_progress(user_id: int, mission_id: str, *, total: int,
                    completed: int, xp_earned: int, hints_used: int,
                    attempts: int, is_complete: bool,
                    started_at: datetime | None = None) -> MissionRecord:
    """Create or update the durable record for a mission session."""
    record = get_record(user_id, mission_id)
    if record is None:
        record = MissionRecord(user_id=user_id, mission_id=mission_id,
                               started_at=started_at)
        db.session.add(record)

    record.objectives_total = total
    record.objectives_completed = completed
    record.xp_earned = xp_earned
    record.hints_used = hints_used
    record.attempts = attempts
    if started_at and not record.started_at:
        record.started_at = started_at

    if is_complete:
        record.status = STATUS_COMPLETED
        if record.completed_at is None:
            from app.models.base import utcnow
            record.completed_at = utcnow()
    else:
        record.status = STATUS_IN_PROGRESS

    db.session.commit()
    return record
