"""Cyber Labs models.

    LabCategory 1 ──< Lab ──< LabObjective
                       │  └──< LabFile
                       └──< UserLabProgress >── 1 User

Mirrors the conventions used by the roadmap and CTF modules: BaseModel for
id/created_at/updated_at, slugs unique and indexed, ordered child
collections with delete-orphan cascades, and the User link attached via
backref so the auth model file stays untouched.

Foundation only — no execution environment, scoring, or hints here.
"""

from __future__ import annotations

import json

from app.extensions import db
from app.models import BaseModel

# Supported difficulty labels (same vocabulary as the CTF module).
LAB_DIFFICULTIES = ("Easy", "Medium", "Hard", "Insane")


class LabCategory(BaseModel):
    """A grouping of labs (e.g. Linux, Networking)."""

    __tablename__ = "lab_categories"

    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=False, default="terminal")
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    labs = db.relationship(
        "Lab",
        back_populates="category",
        order_by="Lab.display_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<LabCategory {self.slug}>"


class Lab(BaseModel):
    """A single hands-on lab."""

    __tablename__ = "labs"

    category_id = db.Column(
        db.Integer, db.ForeignKey("lab_categories.id"), nullable=False, index=True
    )
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=False, default="Easy")
    estimated_minutes = db.Column(db.Integer, nullable=True)
    xp_reward = db.Column(db.Integer, nullable=False, default=0)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # --- Lab Engine (YC-012.1) ---
    # The single dispatch point: which simulator plugin drives this lab.
    # "linux" today; "nmap", "wireshark", "burp"… later — no engine change.
    simulator_key = db.Column(
        db.String(50), nullable=False, default="", index=True
    )
    # Interactive labs get a session + workspace; others stay read-only.
    is_interactive = db.Column(db.Boolean, nullable=False, default=False)
    # Sequential progression (YC-012.3): this lab unlocks once the
    # prerequisite lab is completed. NULL = always unlocked (track entry
    # point). Data-driven, so any future track (Nmap, Wireshark…) gets
    # progression for free — the engine itself is unchanged.
    prerequisite_lab_id = db.Column(
        db.Integer, db.ForeignKey("labs.id"), nullable=True, index=True
    )

    category = db.relationship("LabCategory", back_populates="labs")
    prerequisite = db.relationship(
        "Lab", remote_side="Lab.id", backref="unlocks", uselist=False
    )
    objectives = db.relationship(
        "LabObjective",
        back_populates="lab",
        order_by="LabObjective.display_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    files = db.relationship(
        "LabFile",
        back_populates="lab",
        order_by="LabFile.display_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    progress = db.relationship(
        "UserLabProgress",
        back_populates="lab",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    fs_nodes = db.relationship(
        "LabFileSystemNode",
        back_populates="lab",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sessions = db.relationship(
        "UserLabSession",
        back_populates="lab",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<Lab {self.slug} ({self.difficulty})>"


class LabObjective(BaseModel):
    """One task a lab asks the learner to accomplish."""

    __tablename__ = "lab_objectives"

    lab_id = db.Column(
        db.Integer, db.ForeignKey("labs.id"), nullable=False, index=True
    )
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)

    # --- Lab Engine (YC-012.1) ---
    # What the user is asked to do.
    instruction = db.Column(db.Text, nullable=True)
    # How completion is judged. Capability-neutral: the same two columns
    # serve Terminal, Inspector, Packet Viewer, Browser and Code Editor
    # objectives — only the validator_type differs.
    validator_type = db.Column(db.String(50), nullable=False, default="exact_command")
    validator_data_json = db.Column(db.Text, nullable=False, default="{}")
    # Progressive hints (no penalty; mirrors the CTF hint convention).
    hint1 = db.Column(db.Text, nullable=True)
    hint2 = db.Column(db.Text, nullable=True)
    hint3 = db.Column(db.Text, nullable=True)
    xp_reward = db.Column(db.Integer, nullable=False, default=0)
    is_optional = db.Column(db.Boolean, nullable=False, default=False)

    lab = db.relationship("Lab", back_populates="objectives")
    user_progress = db.relationship(
        "UserObjectiveProgress",
        back_populates="objective",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def get_validator_data(self) -> dict:
        """Validator spec as a dict (stored as text for SQLite friendliness)."""
        try:
            return json.loads(self.validator_data_json or "{}")
        except (TypeError, ValueError):
            return {}

    def set_validator_data(self, data: dict) -> None:
        self.validator_data_json = json.dumps(data or {})

    def hints(self) -> list[str]:
        """Non-empty hints in order."""
        return [h for h in (self.hint1, self.hint2, self.hint3) if h]

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<LabObjective lab={self.lab_id} #{self.display_order}>"


class LabFile(BaseModel):
    """A downloadable/reference file attached to a lab.

    Stores metadata only — no upload or serving behaviour in this ticket.
    """

    __tablename__ = "lab_files"

    lab_id = db.Column(
        db.Integer, db.ForeignKey("labs.id"), nullable=False, index=True
    )
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(400), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)

    lab = db.relationship("Lab", back_populates="files")

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<LabFile {self.filename} (lab {self.lab_id})>"


class UserLabProgress(BaseModel):
    """A user's progress through a lab."""

    __tablename__ = "user_lab_progress"
    __table_args__ = (
        db.UniqueConstraint("user_id", "lab_id", name="uq_user_lab_progress"),
    )

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    lab_id = db.Column(
        db.Integer, db.ForeignKey("labs.id"), nullable=False, index=True
    )
    started = db.Column(db.Boolean, nullable=False, default=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    time_spent_seconds = db.Column(db.Integer, nullable=True)

    lab = db.relationship("Lab", back_populates="progress")
    # Attached from this side so the User model file stays untouched:
    #   some_user.lab_progress -> query of UserLabProgress rows
    user = db.relationship(
        "User",
        backref=db.backref("lab_progress", lazy="dynamic"),
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<UserLabProgress user={self.user_id} lab={self.lab_id}>"


# ===========================================================================
# Lab Engine models (YC-012.1)
#
# DESIGN NOTE — why LabFileSystemNode instead of a generic `LabAsset` blob:
#   A generic (asset_type, payload-JSON) table is untyped, unqueryable and
#   forces every simulator to re-parse an opaque blob. A filesystem is a
#   real, shared structure — Linux, Bash, PowerShell and Python Security all
#   need it — so it earns a proper, indexed table with real columns.
#   Future inspector labs (Wireshark packets, Burp transactions, SOC logs)
#   have genuinely different shapes and will get their own typed tables when
#   they are built. That is cleaner than one speculative catch-all, and the
#   engine does not care either way: it hands a lab's content to the
#   simulator via a content-loader, so adding a table changes no engine code.
# ===========================================================================
class SimulatorEngine(BaseModel):
    """Registry-backed catalogue of available simulators.

    The DB row is metadata (name, description, is_active) — the executable
    plugin lives in code and is resolved by ``key`` through SimulatorRegistry.
    This lets admins see/enable simulators without the engine ever importing
    a concrete simulator class.
    """

    __tablename__ = "simulator_engines"

    key = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # Comma-separated capability hints, e.g. "terminal" or "inspector".
    capabilities = db.Column(db.String(120), nullable=False, default="terminal")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SimulatorEngine {self.key}>"


class LabFileSystemNode(BaseModel):
    """One seeded file or directory in a lab's virtual filesystem.

    Pure data — never touches a real disk. The simulator loads these into
    in-memory session state at bootstrap.
    """

    __tablename__ = "lab_filesystem_nodes"
    __table_args__ = (
        db.UniqueConstraint("lab_id", "path", name="uq_lab_fs_path"),
    )

    lab_id = db.Column(
        db.Integer, db.ForeignKey("labs.id"), nullable=False, index=True
    )
    path = db.Column(db.String(400), nullable=False, index=True)
    node_type = db.Column(db.String(10), nullable=False, default="file")  # file|dir
    content = db.Column(db.Text, nullable=True)
    permissions = db.Column(db.String(16), nullable=False, default="rw-r--r--")
    owner = db.Column(db.String(40), nullable=False, default="user")

    lab = db.relationship("Lab", back_populates="fs_nodes")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LabFileSystemNode {self.path} ({self.node_type})>"


class UserLabSession(BaseModel):
    """A user's live, resumable simulated session for a lab.

    ``state`` is a JSON document owned entirely by the lab's simulator; the
    engine only reads the envelope keys (``sim``, ``version``). State is
    server-side only — the client sends actions, never state.
    """

    __tablename__ = "user_lab_sessions"
    __table_args__ = (
        db.UniqueConstraint("user_id", "lab_id", name="uq_user_lab_session"),
    )

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    lab_id = db.Column(
        db.Integer, db.ForeignKey("labs.id"), nullable=False, index=True
    )
    state_json = db.Column(db.Text, nullable=False, default="{}")
    status = db.Column(db.String(20), nullable=False, default="active")
    last_activity_at = db.Column(db.DateTime(timezone=True), nullable=True)

    lab = db.relationship("Lab", back_populates="sessions")
    user = db.relationship(
        "User", backref=db.backref("lab_sessions", lazy="dynamic")
    )

    # -- state is stored as text so SQLite stays happy; accessed as dict --
    def get_state(self) -> dict:
        try:
            return json.loads(self.state_json or "{}")
        except (TypeError, ValueError):
            return {}

    def set_state(self, state: dict) -> None:
        self.state_json = json.dumps(state or {})

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserLabSession user={self.user_id} lab={self.lab_id}>"


class UserObjectiveProgress(BaseModel):
    """Per-objective completion — the finest grain of lab progress."""

    __tablename__ = "user_objective_progress"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "objective_id", name="uq_user_objective"
        ),
    )

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    objective_id = db.Column(
        db.Integer, db.ForeignKey("lab_objectives.id"), nullable=False, index=True
    )
    completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    objective = db.relationship("LabObjective", back_populates="user_progress")
    user = db.relationship(
        "User", backref=db.backref("objective_progress", lazy="dynamic")
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserObjectiveProgress user={self.user_id} obj={self.objective_id}>"
