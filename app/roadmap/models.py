"""Roadmap learning models.

Content hierarchy and per-user progress:

    RoadmapCategory 1 ──< RoadmapModule 1 ──< Lesson 1 ──< UserLessonProgress >── 1 User

All models inherit ``id``, ``created_at`` and ``updated_at`` from
:class:`app.models.BaseModel`. Content rows (categories, modules,
lessons) carry ``display_order`` for stable curriculum ordering and are
soft-toggled with ``is_active`` rather than deleted, so user progress
history always keeps a valid target.

Per YC-006.2 this file defines ONLY the schema — no seed data, no
services, no unlock logic. The User relationship is attached from this
side (via ``backref``) so ``app/auth/models.py`` stays untouched.
"""

from __future__ import annotations

from app.extensions import db
from app.models import BaseModel


class RoadmapCategory(BaseModel):
    """A top-level learning tier (e.g. Beginner, Intermediate, AI Security)."""

    __tablename__ = "roadmap_categories"

    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Presentation hints consumed by the roadmap UI (icon name + accent color).
    icon = db.Column(db.String(50), nullable=False, default="map")
    color = db.Column(db.String(20), nullable=False, default="green")

    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # One category -> many modules, kept in curriculum order.
    modules = db.relationship(
        "RoadmapModule",
        back_populates="category",
        order_by="RoadmapModule.display_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<RoadmapCategory {self.title}>"


class RoadmapModule(BaseModel):
    """A course-sized unit inside a category (e.g. 'Linux Essentials')."""

    __tablename__ = "roadmap_modules"

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("roadmap_categories.id"),
        nullable=False,
        index=True,
    )

    title = db.Column(db.String(150), nullable=False)
    # Globally unique URL identifier (e.g. 'linux-essentials').
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    # beginner | intermediate | advanced | expert — validated at the
    # service layer when content management lands.
    difficulty = db.Column(db.String(20), nullable=False, default="beginner")
    estimated_hours = db.Column(db.Integer, nullable=False, default=1)
    xp_reward = db.Column(db.Integer, nullable=False, default=0)

    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_locked = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    category = db.relationship("RoadmapCategory", back_populates="modules")

    # One module -> many lessons, kept in curriculum order.
    lessons = db.relationship(
        "Lesson",
        back_populates="module",
        order_by="Lesson.display_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<RoadmapModule {self.slug}>"


class Lesson(BaseModel):
    """A single learning unit inside a module."""

    __tablename__ = "lessons"
    __table_args__ = (
        # Lesson slugs are unique within their module (two modules may both
        # have an 'introduction' lesson), unlike globally-unique module slugs.
        db.UniqueConstraint("module_id", "slug", name="uq_lesson_module_slug"),
    )

    module_id = db.Column(
        db.Integer,
        db.ForeignKey("roadmap_modules.id"),
        nullable=False,
        index=True,
    )

    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), nullable=False)

    # Path to the lesson content file (markdown/HTML), relative to the
    # future content root — keeps large content out of the database.
    content_path = db.Column(db.String(255), nullable=True)

    # reading | video | lab | quiz — validated at the service layer later.
    lesson_type = db.Column(db.String(20), nullable=False, default="reading")
    estimated_minutes = db.Column(db.Integer, nullable=False, default=10)
    xp_reward = db.Column(db.Integer, nullable=False, default=0)

    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    # Preview lessons are viewable without unlocking the module.
    is_preview = db.Column(db.Boolean, nullable=False, default=False)

    module = db.relationship("RoadmapModule", back_populates="lessons")

    # One lesson -> many per-user progress rows.
    progress_records = db.relationship(
        "UserLessonProgress",
        back_populates="lesson",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<Lesson {self.slug} (module {self.module_id})>"


class UserLessonProgress(BaseModel):
    """One user's progress on one lesson (at most one row per pair)."""

    __tablename__ = "user_lesson_progress"
    __table_args__ = (
        db.UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    lesson_id = db.Column(
        db.Integer, db.ForeignKey("lessons.id"), nullable=False, index=True
    )

    completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_opened = db.Column(db.DateTime(timezone=True), nullable=True)

    # Accumulated seconds spent in the lesson.
    time_spent = db.Column(db.Integer, nullable=False, default=0)
    # Quiz/lab score (0–100); NULL for lesson types without scoring.
    score = db.Column(db.Integer, nullable=True)

    lesson = db.relationship("Lesson", back_populates="progress_records")

    # Attach the relationship to User from THIS side (backref) so the
    # existing auth model file does not need to be modified:
    #   some_user.lesson_progress -> query of UserLessonProgress rows
    user = db.relationship(
        "User",
        backref=db.backref("lesson_progress", lazy="dynamic"),
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<UserLessonProgress user={self.user_id} lesson={self.lesson_id}>"


class UserModuleProgress(BaseModel):
    """One user's progression state for one module (at most one row per pair).

    Per-user unlock/completion state, replacing the deprecated global
    ``RoadmapModule.is_locked`` flag. ``bonus_awarded`` guards the
    module's one-time XP bonus so it can never be granted twice.
    """

    __tablename__ = "user_module_progress"
    __table_args__ = (
        db.UniqueConstraint("user_id", "module_id", name="uq_module_progress_user_module"),
    )

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    module_id = db.Column(
        db.Integer, db.ForeignKey("roadmap_modules.id"), nullable=False, index=True
    )

    unlocked = db.Column(db.Boolean, nullable=False, default=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    bonus_awarded = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    module = db.relationship("RoadmapModule", backref=db.backref(
        "user_progress", lazy="dynamic", cascade="all, delete-orphan"))

    # Attached from this side so the User model file stays untouched:
    #   some_user.module_progress -> query of UserModuleProgress rows
    user = db.relationship(
        "User",
        backref=db.backref("module_progress", lazy="dynamic"),
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"<UserModuleProgress user={self.user_id} module={self.module_id}>"
