"""CTF models.

    ChallengeCategory 1 ──< Challenge 1 ──< ChallengeSolve >── 1 User

Flags are hashed with Werkzeug (scrypt), matching how the project stores
passwords — the raw flag is never persisted. ``ChallengeSolve`` records a
user's progress on a challenge (attempts, solved state) with a unique
(user_id, challenge_id) constraint. All inherit id/created_at/updated_at
from BaseModel. The User relationship is attached via backref so the auth
model file stays untouched.

This foundation ticket defines schema + flag hashing only; no XP,
achievements, or UI here.
"""

from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import BaseModel

# Supported difficulty labels.
DIFFICULTIES = ("Easy", "Medium", "Hard", "Insane")


class ChallengeCategory(BaseModel):
    """A grouping of CTF challenges (e.g. Web Security)."""

    __tablename__ = "challenge_categories"

    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=False, default="flag")
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    challenges = db.relationship(
        "Challenge",
        back_populates="category",
        order_by="Challenge.display_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<ChallengeCategory {self.slug}>"


class Challenge(BaseModel):
    """A single CTF challenge."""

    __tablename__ = "challenges"

    category_id = db.Column(
        db.Integer, db.ForeignKey("challenge_categories.id"),
        nullable=False, index=True,
    )
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=False, default="Easy")

    # Flag stored hashed (scrypt) — the raw value is never persisted.
    flag_hash = db.Column(db.String(255), nullable=False)

    xp_reward = db.Column(db.Integer, nullable=False, default=0)
    points = db.Column(db.Integer, nullable=False, default=0)
    hint = db.Column(db.Text, nullable=True)
    author = db.Column(db.String(80), nullable=True)
    estimated_minutes = db.Column(db.Integer, nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    category = db.relationship("ChallengeCategory", back_populates="challenges")
    solves = db.relationship(
        "ChallengeSolve",
        back_populates="challenge",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    hints = db.relationship(
        "ChallengeHint",
        back_populates="challenge",
        order_by="ChallengeHint.display_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def set_flag(self, flag: str) -> None:
        """Hash and store a flag (raw value never persisted)."""
        self.flag_hash = generate_password_hash(flag)

    def check_flag(self, flag: str) -> bool:
        """Constant-time comparison of a submitted flag against the hash."""
        if not self.flag_hash or flag is None:
            return False
        return check_password_hash(self.flag_hash, flag)

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<Challenge {self.slug} ({self.difficulty})>"


class ChallengeSolve(BaseModel):
    """A user's progress on a challenge (attempts + solved state)."""

    __tablename__ = "challenge_solves"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "challenge_id", name="uq_challenge_solve"
        ),
    )

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id"), nullable=False, index=True
    )
    solved = db.Column(db.Boolean, nullable=False, default=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    solved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    time_taken_seconds = db.Column(db.Integer, nullable=True)

    challenge = db.relationship("Challenge", back_populates="solves")
    # Attached from this side so the User model file stays untouched:
    #   some_user.challenge_solves -> query of ChallengeSolve rows
    user = db.relationship(
        "User",
        backref=db.backref("challenge_solves", lazy="dynamic"),
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<ChallengeSolve user={self.user_id} challenge={self.challenge_id} solved={self.solved}>"


class ChallengeHint(BaseModel):
    """One hint attached to a challenge.

    A challenge may have several hints, revealed independently in the UI.
    ``is_free`` marks hints that will remain penalty-free once a penalty
    system exists (no penalties are applied today — YC-010.6 is
    display-only).
    """

    __tablename__ = "challenge_hints"

    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id"), nullable=False, index=True
    )
    title = db.Column(db.String(150), nullable=True)
    content = db.Column(db.Text, nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_free = db.Column(db.Boolean, nullable=False, default=True)

    challenge = db.relationship("Challenge", back_populates="hints")

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<ChallengeHint challenge={self.challenge_id} #{self.display_order}>"
