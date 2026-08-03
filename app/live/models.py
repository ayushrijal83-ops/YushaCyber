"""Live classroom models."""

from __future__ import annotations

from app.extensions import db
from app.auth.models import BaseModel


CLASS_STATUSES = ("draft", "scheduled", "live", "ended",
                  "cancelled", "archived")
ATTENDANCE_STATUSES = ("registered", "present", "late", "absent")
PROVIDERS = ("jitsi", "zoom", "google_meet", "teams")


class LiveClass(BaseModel):
    __tablename__ = "live_classes"

    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True,
                     index=True)
    description = db.Column(db.Text, nullable=True)
    instructor_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False,
        index=True)
    category = db.Column(db.String(50), nullable=False, default="general")
    difficulty = db.Column(db.String(20), nullable=False, default="Easy")
    start_time = db.Column(db.DateTime(timezone=True), nullable=True)
    end_time = db.Column(db.DateTime(timezone=True), nullable=True)
    timezone = db.Column(db.String(50), nullable=False, default="UTC")
    meeting_provider = db.Column(db.String(30), nullable=False,
                                 default="jitsi")
    meeting_url = db.Column(db.String(500), nullable=True)
    meeting_room = db.Column(db.String(100), nullable=True)
    capacity = db.Column(db.Integer, nullable=False, default=30)
    visibility = db.Column(db.String(20), nullable=False, default="public")
    status = db.Column(db.String(20), nullable=False, default="draft",
                       index=True)
    recurring_rule = db.Column(db.String(200), nullable=True)

    instructor = db.relationship("User", backref="taught_classes",
                                 lazy="selectin")
    enrollments = db.relationship("Enrollment", backref="live_class",
                                  cascade="all, delete-orphan",
                                  lazy="selectin")
    resources = db.relationship("ClassResource", backref="live_class",
                                cascade="all, delete-orphan",
                                lazy="selectin")

    @property
    def enrolled_count(self) -> int:
        return len(self.enrollments or [])

    @property
    def is_full(self) -> bool:
        return self.enrolled_count >= self.capacity

    def is_instructor(self, user) -> bool:
        return self.instructor_id == user.id


class Enrollment(BaseModel):
    __tablename__ = "live_enrollments"

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    class_id = db.Column(
        db.Integer, db.ForeignKey("live_classes.id", ondelete="CASCADE"),
        nullable=False, index=True)
    attendance_status = db.Column(db.String(20), nullable=False,
                                  default="registered")
    joined_at = db.Column(db.DateTime(timezone=True), nullable=True)
    left_at = db.Column(db.DateTime(timezone=True), nullable=True)
    attendance_duration = db.Column(db.Integer, nullable=True)
    certificate_eligible = db.Column(db.Boolean, nullable=False,
                                     default=False)

    user = db.relationship("User", backref="class_enrollments",
                           lazy="selectin")

    __table_args__ = (
        db.UniqueConstraint("user_id", "class_id",
                            name="uq_enrollment"),
    )


class ClassResource(BaseModel):
    __tablename__ = "live_class_resources"

    class_id = db.Column(
        db.Integer, db.ForeignKey("live_classes.id", ondelete="CASCADE"),
        nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=True)
    resource_type = db.Column(db.String(30), nullable=False,
                              default="document")
    url = db.Column(db.String(500), nullable=True)
