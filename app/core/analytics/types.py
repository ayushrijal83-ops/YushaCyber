"""Analytics types — metric definitions, summaries, and insights."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StudentMetrics:
    """Per-student analytics snapshot."""
    student_id: int = 0
    username: str = ""
    total_xp: int = 0
    xp_this_week: int = 0
    xp_this_month: int = 0
    level: int = 1
    completed_labs: int = 0
    total_labs: int = 0
    completed_tracks: int = 0
    completion_rate: float = 0.0
    average_score: float = 0.0
    average_grade: str = ""
    average_time_seconds: int = 0
    certificates_earned: int = 0
    achievements_earned: int = 0
    hints_used: int = 0
    attempts: int = 0
    perfect_scores: int = 0
    current_streak: int = 0
    highest_streak: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrackMetrics:
    """Per-track analytics."""
    track_slug: str = ""
    track_name: str = ""
    total_labs: int = 0
    completion_pct: float = 0.0
    average_time_seconds: int = 0
    difficulty_distribution: dict[str, int] = field(default_factory=dict)
    most_completed_lab: str = ""
    least_completed_lab: str = ""
    enrolled_students: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AssessmentMetrics:
    """Assessment-level analytics."""
    assessment_slug: str = ""
    total_attempts: int = 0
    pass_rate: float = 0.0
    fail_rate: float = 0.0
    average_grade: str = ""
    grade_distribution: dict[str, int] = field(default_factory=dict)
    score_distribution: dict[str, int] = field(default_factory=dict)
    average_attempts: float = 0.0
    average_time_seconds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EngagementMetrics:
    """Platform engagement analytics."""
    daily_active: int = 0
    weekly_active: int = 0
    monthly_active: int = 0
    average_streak: float = 0.0
    average_study_minutes: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdminDashboard:
    """Admin-level platform summary."""
    total_students: int = 0
    online_students: int = 0
    total_xp_earned: int = 0
    certificates_issued: int = 0
    achievements_unlocked: int = 0
    labs_completed: int = 0
    top_students: list[dict[str, Any]] = field(default_factory=list)
    most_popular_track: str = ""
    least_completed_track: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Insight:
    """An automatically generated learning insight."""
    category: str = ""       # student | track | platform
    severity: str = "info"   # info | warning | success
    message: str = ""
    metric_key: str = ""
    metric_value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
