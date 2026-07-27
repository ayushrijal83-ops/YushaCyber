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
    #: Expected student answer — which classification is correct.
    expected_classification = db.Column(
        db.String(20), nullable=True)
    #: Expected root-cause keywords for validation.
    expected_root_cause = db.Column(db.String(200), nullable=True)
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


# ===========================================================================
# Case Management (YC-030.3.5)
# ===========================================================================
CASE_STATUSES = ("new", "in_progress", "escalated", "resolved", "closed")


class SocCase(BaseModel):
    """A reusable SOC case that aggregates alerts, notes and evidence
    links. Every future SOC investigation scenario creates/manages
    cases through this model."""

    __tablename__ = "soc_cases"

    case_code = db.Column(db.String(60), nullable=False, unique=True,
                          index=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new",
                       index=True)
    severity = db.Column(db.String(20), nullable=False, default="medium",
                         index=True)
    assigned_analyst = db.Column(db.String(80), nullable=True)
    closed_at = db.Column(db.String(40), nullable=True)

    #: JSON-serialised list of linked alert codes.
    linked_alert_codes_json = db.Column(db.Text, nullable=False,
                                        default="[]")
    #: JSON-serialised list of linked evidence slugs / artifact ids.
    linked_evidence_json = db.Column(db.Text, nullable=False,
                                     default="[]")
    #: Free-form investigation-progress percentage (0–100).
    progress = db.Column(db.Integer, nullable=False, default=0)

    def is_open(self) -> bool:
        return self.status in ("new", "in_progress", "escalated")

    # ---- JSON helpers ----
    def get_linked_alerts(self) -> list[str]:
        import json as _json
        try:
            return _json.loads(self.linked_alert_codes_json or "[]")
        except (TypeError, ValueError):
            return []

    def set_linked_alerts(self, codes: list[str]) -> None:
        import json as _json
        self.linked_alert_codes_json = _json.dumps(codes or [])

    def get_linked_evidence(self) -> list:
        import json as _json
        try:
            return _json.loads(self.linked_evidence_json or "[]")
        except (TypeError, ValueError):
            return []

    def set_linked_evidence(self, items: list) -> None:
        import json as _json
        self.linked_evidence_json = _json.dumps(items or [])


class SocCaseNote(BaseModel):
    """One note attached to a SOC case."""

    __tablename__ = "soc_case_notes"

    soc_case_id = db.Column(
        db.Integer, db.ForeignKey("soc_cases.id", ondelete="CASCADE"),
        nullable=False, index=True)
    author = db.Column(db.String(80), nullable=False, default="analyst")
    text = db.Column(db.Text, nullable=False)

    case = db.relationship(
        "SocCase",
        backref=db.backref("notes", cascade="all, delete-orphan",
                           lazy="selectin",
                           order_by="SocCaseNote.created_at"))


# ===========================================================================
# Threat Hunting (YC-030.6)
# ===========================================================================
class SocHunt(BaseModel):
    """A threat hunt scenario — students search telemetry proactively."""

    __tablename__ = "soc_hunts"

    slug = db.Column(db.String(80), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    hypothesis = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    difficulty = db.Column(db.String(20), nullable=False, default="Expert")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    #: Link to a ForensicsCase that holds the telemetry artifacts.
    case_id = db.Column(
        db.Integer, db.ForeignKey("forensics_cases.id", ondelete="SET NULL"),
        nullable=True, index=True)
    case = db.relationship("ForensicsCase", lazy="joined")


class SocIOC(BaseModel):
    """An Indicator of Compromise seeded into a hunt."""

    __tablename__ = "soc_iocs"

    hunt_id = db.Column(
        db.Integer, db.ForeignKey("soc_hunts.id", ondelete="CASCADE"),
        nullable=False, index=True)
    ioc_type = db.Column(db.String(30), nullable=False, index=True)
    value = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    is_malicious = db.Column(db.Boolean, nullable=False, default=False)
    #: MITRE ATT&CK technique ID (e.g. "T1059.001").
    mitre_technique = db.Column(db.String(20), nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)

    hunt = db.relationship(
        "SocHunt",
        backref=db.backref("iocs", cascade="all, delete-orphan",
                           lazy="selectin",
                           order_by="SocIOC.display_order"))


IOC_TYPES = (
    "ip", "domain", "sha256", "filename", "url",
    "registry_key", "scheduled_task", "service",
    "process", "command_line", "dns_query",
)


# ===========================================================================
# Blue Team Assessment (YC-030.7)
# ===========================================================================
class AssessmentResult(BaseModel):
    """Records a student's final assessment score for the leaderboard."""

    __tablename__ = "soc_assessment_results"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id",
                        ondelete="CASCADE"), nullable=False, index=True)
    assessment_slug = db.Column(db.String(80), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False, default=0)
    max_score = db.Column(db.Integer, nullable=False, default=100)
    grade = db.Column(db.String(30), nullable=False, default="")
    completion_seconds = db.Column(db.Integer, nullable=True)
    certificate_id_str = db.Column(db.String(40), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "assessment_slug",
                            name="uq_assessment_result"),
    )
