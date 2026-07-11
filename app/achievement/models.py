"""Achievement models.

    Achievement 1 ──< UserAchievement >── 1 User

An ``Achievement`` is a definition (title, unlock condition, bonus XP).
A ``UserAchievement`` records that a specific user has unlocked one, with
a unique (user_id, achievement_id) constraint so an achievement can never
be unlocked twice for the same user. Both inherit id/created_at/updated_at
from BaseModel. The User relationship is attached from this side via
backref so the auth model file stays untouched.

This foundation ticket defines schema + a condition vocabulary only; no
automatic unlocking logic lives here.
"""

from __future__ import annotations

from app.extensions import db
from app.models import BaseModel


class Achievement(BaseModel):
    """A single achievement definition."""

    __tablename__ = "achievements"

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=False, default="award")
    # Grouping label, e.g. "lessons", "quizzes", "progression".
    category = db.Column(db.String(50), nullable=False, default="general")

    # Condition vocabulary consumed by the (future) auto-unlock engine:
    # e.g. "lessons_completed", "quizzes_passed", "level_reached",
    # "xp_earned", "perfect_quiz", "modules_completed".
    condition_type = db.Column(db.String(50), nullable=False)
    condition_value = db.Column(db.Integer, nullable=False, default=1)

    bonus_xp = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)

    # One achievement -> many per-user unlock rows.
    user_unlocks = db.relationship(
        "UserAchievement",
        back_populates="achievement",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<Achievement {self.title}>"


class UserAchievement(BaseModel):
    """Records that a user has unlocked an achievement (once)."""

    __tablename__ = "user_achievements"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "achievement_id", name="uq_user_achievement"
        ),
    )

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    achievement_id = db.Column(
        db.Integer, db.ForeignKey("achievements.id"), nullable=False, index=True
    )
    unlocked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    achievement = db.relationship("Achievement", back_populates="user_unlocks")
    # Attached from this side so the User model file stays untouched:
    #   some_user.achievements -> query of UserAchievement rows
    user = db.relationship(
        "User",
        backref=db.backref("achievements", lazy="dynamic"),
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<UserAchievement user={self.user_id} achievement={self.achievement_id}>"
