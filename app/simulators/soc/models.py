"""SOC Analyst Simulator models (YC-030.1).

A SOC Alert links an entry on the analyst queue to an underlying
``ForensicsCase`` — investigating the alert IS investigating the case
with all its evidence, sources, artifacts, suspects and correlations
already provided by the Digital Forensics engines. Nothing here
duplicates that data; alerts merely wrap it with a triage envelope
(severity / status / source / assignee) and reference the playbook
that guides the response.

Playbooks are static content per ``alert_type``: an ordered list of
step rows organised into IR-lifecycle phases (Identification,
Containment, Eradication, Recovery, Lessons Learned).

Checklist items live per case — a short set of investigation tasks
the student ticks off during the workflow. Completion state is
session-only; the row here is just the definition.
"""

from __future__ import annotations

from app.extensions import db
from app.models.base import BaseModel

#: The severity buckets a SOC alert can carry.
SEVERITIES = ("critical", "high", "medium", "low", "informational")

#: Alert workflow states.
STATUSES = ("open", "in_progress", "resolved", "closed", "false_positive")

#: Alert types the fundamentals lab seeds; more can be added later.
ALERT_TYPES = (
    "multiple_failed_logins", "suspicious_powershell",
    "possible_malware", "dns_tunneling",
    "suspicious_http_traffic", "usb_activity",
    "privilege_escalation", "data_exfiltration",
)

#: IR-lifecycle phases used by playbooks.
PLAYBOOK_PHASES = (
    "identification", "containment", "eradication",
    "recovery", "lessons_learned",
)


class SocAlert(BaseModel):
    """One alert on the analyst queue."""

    __tablename__ = "soc_alerts"

    #: Stable public id shown in the UI (e.g. "ALERT-2026-0007").
    alert_code = db.Column(db.String(30), unique=True, nullable=False,
                           index=True)
    title = db.Column(db.String(200), nullable=False)
    alert_type = db.Column(db.String(40), nullable=False, index=True)
    severity = db.Column(db.String(15), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="open",
                       index=True)
    source = db.Column(db.String(80), nullable=False, default="SIEM")
    assigned_analyst = db.Column(db.String(80), nullable=True)
    #: ISO-ish string shown in the queue and dashboard.
    at_time = db.Column(db.String(30), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    #: When set, the alert links to a ForensicsCase — investigating
    #: the alert means walking the case's evidence and closing it.
    case_id = db.Column(
        db.Integer, db.ForeignKey("forensics_cases.id",
                                  ondelete="SET NULL"),
        nullable=True, index=True)

    case = db.relationship("ForensicsCase", lazy="joined")


class SocPlaybook(BaseModel):
    """A response playbook — one per ``alert_type``."""

    __tablename__ = "soc_playbooks"

    alert_type = db.Column(db.String(40), unique=True, nullable=False,
                           index=True)
    title = db.Column(db.String(160), nullable=False)
    summary = db.Column(db.Text, nullable=False, default="")

    steps = db.relationship(
        "SocPlaybookStep", back_populates="playbook",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="SocPlaybookStep.display_order")


class SocPlaybookStep(BaseModel):
    """One row in a playbook (Identification → Lessons Learned)."""

    __tablename__ = "soc_playbook_steps"

    playbook_id = db.Column(
        db.Integer, db.ForeignKey("soc_playbooks.id", ondelete="CASCADE"),
        nullable=False, index=True)
    #: Which IR-lifecycle phase this step belongs to.
    phase = db.Column(db.String(20), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    display_order = db.Column(db.Integer, nullable=False, default=0,
                              index=True)

    playbook = db.relationship("SocPlaybook", back_populates="steps")


class SocChecklistItem(BaseModel):
    """One tick-box the analyst works through for a given case."""

    __tablename__ = "soc_checklist_items"

    case_id = db.Column(
        db.Integer, db.ForeignKey("forensics_cases.id",
                                  ondelete="CASCADE"),
        nullable=False, index=True)
    #: Stable slug — the state stores which slugs the analyst has
    #: ticked off, so re-seeding is safe.
    slug = db.Column(db.String(60), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    is_required = db.Column(db.Boolean, nullable=False, default=True)
    display_order = db.Column(db.Integer, nullable=False, default=0,
                              index=True)

    __table_args__ = (
        db.UniqueConstraint("case_id", "slug",
                            name="uq_soc_checklist_slug"),
    )
