"""Digital Forensics models (YC-029.5.2).

The forensic case data an admin can edit — everything is simulated data
never touched by any real tool. A ``ForensicsCase`` groups
``ForensicsEvidence`` items (files, USB devices, browser history) and
``ForensicsTimelineEvent`` rows. Each case is scoped to a lab by slug,
so admins can create new cases by seeding new labs.

Nothing here reads the host filesystem. All hashes are deterministic
simulated values produced by ``engine.simulated_hash``.
"""

from __future__ import annotations

import json as _json

from app.extensions import db
from app.models.base import BaseModel

#: Evidence categories rendered in the explorer sidebar.
EVIDENCE_KINDS = (
    "document", "image", "pdf", "archive",
    "usb", "browser", "download", "recycle_bin",
)

#: A timeline event is an ordered pair of (hh:mm, action).
TIMELINE_KINDS = (
    "login", "usb", "file_created", "file_modified",
    "download", "recycle_bin", "logout", "other",
)


class ForensicsCase(BaseModel):
    """One investigative scenario — attached to a lab by slug."""

    __tablename__ = "forensics_cases"

    lab_slug = db.Column(db.String(150), unique=True, nullable=False,
                        index=True)
    title = db.Column(db.String(160), nullable=False)
    briefing = db.Column(db.Text, nullable=False, default="")
    workstation_name = db.Column(db.String(80), nullable=False,
                                 default="WORKSTATION-01")
    investigator = db.Column(db.String(80), nullable=False,
                             default="Investigator Ayush")
    #: "fundamentals" (YC-029.5.2) or "applied" (YC-029.5.3). Drives
    #: which panel set the workspace renders and which validator shape
    #: `evaluate_findings` uses.
    mode = db.Column(db.String(20), nullable=False,
                     default="fundamentals",
                     server_default="fundamentals")

    evidence = db.relationship(
        "ForensicsEvidence", back_populates="case",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="ForensicsEvidence.display_order")
    timeline = db.relationship(
        "ForensicsTimelineEvent", back_populates="case",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="ForensicsTimelineEvent.at_time")

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<ForensicsCase {self.lab_slug}>"


class ForensicsEvidence(BaseModel):
    """One piece of simulated evidence with metadata."""

    __tablename__ = "forensics_evidence"

    case_id = db.Column(
        db.Integer, db.ForeignKey("forensics_cases.id", ondelete="CASCADE"),
        nullable=False, index=True)
    #: Stable slug used as the id in the UI (e.g. "confidential-pdf").
    slug = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(20), nullable=False, default="document")
    filename = db.Column(db.String(160), nullable=False)
    extension = db.Column(db.String(20), nullable=False, default="")
    owner = db.Column(db.String(60), nullable=False, default="user")
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    #: ISO-ish times ("2026-04-17 08:12" is fine — they're display strings).
    created_at_display = db.Column(db.String(40), nullable=False,
                                   default="")
    modified_at_display = db.Column(db.String(40), nullable=False,
                                    default="")
    #: Optional snippet shown in the metadata panel (never a real file).
    notes = db.Column(db.Text, nullable=True)
    is_suspicious = db.Column(db.Boolean, nullable=False, default=False)
    is_modified = db.Column(db.Boolean, nullable=False, default=False)
    display_order = db.Column(db.Integer, nullable=False, default=0,
                              index=True)

    case = db.relationship("ForensicsCase", back_populates="evidence")

    __table_args__ = (
        db.UniqueConstraint("case_id", "slug",
                            name="uq_forensics_evidence_slug"),
    )


class ForensicsTimelineEvent(BaseModel):
    """One row on the workstation activity timeline."""

    __tablename__ = "forensics_timeline_events"

    case_id = db.Column(
        db.Integer, db.ForeignKey("forensics_cases.id", ondelete="CASCADE"),
        nullable=False, index=True)
    at_time = db.Column(db.String(8), nullable=False)  # "HH:MM"
    kind = db.Column(db.String(20), nullable=False, default="other")
    description = db.Column(db.String(200), nullable=False)
    #: Optional linkage to an evidence slug (highlights the panel when
    #: the row is clicked).
    evidence_slug = db.Column(db.String(80), nullable=True)

    case = db.relationship("ForensicsCase", back_populates="timeline")


# ===========================================================================
# Applied lab (YC-029.5.3): generic artifact source table.
#
# One row per artifact (browser visit, downloaded file, event log entry,
# USB connection, login session, recent document). ``source_type`` is
# the discriminator; ``data`` is a JSON blob with source-specific
# fields so future SOC / threat hunting / incident response labs add
# new source types by seeding rows — no migration required.
# ===========================================================================
#: The source types this ticket ships. Future labs may add more.
ARTIFACT_SOURCES = (
    "browser_history", "downloads", "event_log",
    "usb_history", "login_history", "recent_docs",
)


class ForensicsArtifact(BaseModel):
    """One row from a simulated evidence source (browser, logs, USB…)."""

    __tablename__ = "forensics_artifacts"

    case_id = db.Column(
        db.Integer, db.ForeignKey("forensics_cases.id",
                                  ondelete="CASCADE"),
        nullable=False, index=True)
    source_type = db.Column(db.String(30), nullable=False, index=True)
    #: Sortable timestamp — "HH:MM" for same-day events or ISO-ish
    #: strings for older sessions. Sort is lexicographic, so "08:12"
    #: precedes "10:05". Cross-day timelines can use "2026-04-17 08:12".
    at_time = db.Column(db.String(40), nullable=False, index=True)
    #: JSON blob of source-specific fields (see engine.ARTIFACT_SCHEMA).
    data_json = db.Column(db.Text, nullable=False, default="{}")
    #: Optional flag — if true, the applied validator expects the
    #: student to identify this row (e.g. the suspicious website).
    is_key = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0,
                           index=True)

    case = db.relationship("ForensicsCase",
                           backref=db.backref("artifacts",
                                              cascade="all, delete-orphan",
                                              lazy="selectin",
                                              order_by="ForensicsArtifact.at_time"))

    def get_data(self) -> dict:
        try:
            return _json.loads(self.data_json or "{}")
        except (TypeError, ValueError):
            return {}

    def set_data(self, data: dict) -> None:
        self.data_json = _json.dumps(data or {})

