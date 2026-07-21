"""Community platform models (YC-034.0).

Teams, classrooms, assignments, discussions, notifications and
announcements. Everything here is NEW schema layered on top of the
existing systems — progress, XP, certificates and achievements stay
exactly where they are and are only *referenced*, never duplicated.
Assignment completion, for example, is resolved live from the existing
progress tables rather than stored twice.
"""

from __future__ import annotations

import secrets

from app.extensions import db
from app.models.base import BaseModel

#: Subjects an assignment may point at (resolved against existing tables).
ASSIGNMENT_SUBJECTS = ("roadmap", "lesson", "lab", "ctf", "quiz")
#: Subjects a discussion may hang off.
DISCUSSION_SUBJECTS = ("lab", "lesson")
#: Notification types the engine emits.
NOTIFICATION_TYPES = (
    "team_invite", "team_joined", "classroom_added", "assignment_new",
    "announcement", "achievement", "certificate",
)


# ===========================================================================
# Teams
# ===========================================================================
class Team(BaseModel):
    __tablename__ = "teams"

    name = db.Column(db.String(60), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    #: Emoji / short glyph shown as the team logo.
    logo = db.Column(db.String(10), nullable=False, default="🛡️")
    #: Open teams can be joined directly; closed teams need an invite.
    is_open = db.Column(db.Boolean, nullable=False, default=True)
    captain_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True)

    members = db.relationship(
        "TeamMember", back_populates="team",
        cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<Team {self.slug}>"


class TeamMember(BaseModel):
    __tablename__ = "team_members"
    __table_args__ = (
        # A user belongs to at most ONE team — classic CTF-team rule.
        db.UniqueConstraint("user_id", name="uq_team_member_user"),
    )

    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False, index=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    joined_at = db.Column(db.DateTime(timezone=True), nullable=True)

    team = db.relationship("Team", back_populates="members")
    user = db.relationship("User", lazy="joined")


class TeamInvite(BaseModel):
    __tablename__ = "team_invites"
    __table_args__ = (
        # One live invite per (team, invitee) — invites are deleted on
        # accept/decline, so no resolved-history rows accumulate.
        db.UniqueConstraint("team_id", "invitee_id",
                            name="uq_team_invite"),
    )

    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False, index=True)
    inviter_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False)
    invitee_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    #: pending | accepted | declined
    status = db.Column(db.String(12), nullable=False, default="pending",
                       index=True)

    team = db.relationship("Team", lazy="joined")


# ===========================================================================
# Classrooms
# ===========================================================================
def _join_code() -> str:
    return secrets.token_hex(4).upper()


class Classroom(BaseModel):
    __tablename__ = "classrooms"

    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    join_code = db.Column(db.String(12), unique=True, nullable=False,
                          default=_join_code, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    teacher = db.relationship("User", lazy="joined")
    members = db.relationship(
        "ClassroomMember", back_populates="classroom",
        cascade="all, delete-orphan", lazy="selectin")
    assignments = db.relationship(
        "Assignment", back_populates="classroom",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="Assignment.created_at.desc()")

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<Classroom {self.name}>"


class ClassroomMember(BaseModel):
    __tablename__ = "classroom_members"
    __table_args__ = (
        db.UniqueConstraint("classroom_id", "user_id",
                            name="uq_classroom_member"),
    )

    classroom_id = db.Column(
        db.Integer, db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False, index=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True)

    classroom = db.relationship("Classroom", back_populates="members")
    user = db.relationship("User", lazy="joined")


# ===========================================================================
# Assignments — resolved live against the existing progress tables.
# ===========================================================================
class Assignment(BaseModel):
    __tablename__ = "assignments"

    classroom_id = db.Column(
        db.Integer, db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False, index=True)
    #: roadmap | lesson | lab | ctf | quiz
    subject_type = db.Column(db.String(12), nullable=False)
    subject_id = db.Column(db.Integer, nullable=False)
    #: Snapshot of the subject's title at assignment time.
    title = db.Column(db.String(160), nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    due_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True)

    classroom = db.relationship("Classroom", back_populates="assignments")


# ===========================================================================
# Discussions — every lab and lesson gets a thread board.
# ===========================================================================
class DiscussionThread(BaseModel):
    __tablename__ = "discussion_threads"

    subject_type = db.Column(db.String(12), nullable=False, index=True)
    subject_id = db.Column(db.Integer, nullable=False, index=True)
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    #: Questions can receive a pinned (accepted) answer.
    is_question = db.Column(db.Boolean, nullable=False, default=False)
    pinned_reply_id = db.Column(db.Integer, nullable=True)

    author = db.relationship("User", lazy="joined")
    replies = db.relationship(
        "DiscussionReply", back_populates="thread",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="DiscussionReply.created_at.asc()")


class DiscussionReply(BaseModel):
    __tablename__ = "discussion_replies"

    thread_id = db.Column(
        db.Integer,
        db.ForeignKey("discussion_threads.id", ondelete="CASCADE"),
        nullable=False, index=True)
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False)
    body = db.Column(db.Text, nullable=False)

    thread = db.relationship("DiscussionThread", back_populates="replies")
    author = db.relationship("User", lazy="joined")


# ===========================================================================
# Notifications + announcements
# ===========================================================================
class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    type = db.Column(db.String(24), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.String(300), nullable=False, default="")
    #: In-app link the notification points at.
    link = db.Column(db.String(255), nullable=False, default="")
    is_read = db.Column(db.Boolean, nullable=False, default=False,
                        index=True)


class Announcement(BaseModel):
    __tablename__ = "announcements"

    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True)
    #: NULL classroom -> global (platform-wide, admin only).
    classroom_id = db.Column(
        db.Integer, db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=True, index=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)

    author = db.relationship("User", lazy="joined")
