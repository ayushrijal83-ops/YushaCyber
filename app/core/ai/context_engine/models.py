"""Context engine models — rich structured context."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class UserContext:
    user_id: int = 0
    username: str = ""
    role: str = "student"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearningContext:
    current_track: str = ""
    current_module: str = ""
    current_lesson: str = ""
    current_lab: str = ""
    current_lab_title: str = ""
    current_scenario: str = ""
    current_objective: str = ""
    difficulty: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressContext:
    xp: int = 0
    level: int = 1
    completion_pct: float = 0.0
    objectives_completed: int = 0
    labs_completed: int = 0
    lessons_completed: int = 0
    total_labs: int = 0
    current_streak: int = 0
    average_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActivityContext:
    current_page: str = ""
    time_spent_seconds: int = 0
    last_action: str = ""
    recent_pages: list[str] = field(default_factory=list)
    recent_labs: list[str] = field(default_factory=list)
    recent_lessons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AssessmentContext:
    attempts: int = 0
    success_rate: float = 0.0
    hint_usage: int = 0
    failed_objectives: list[str] = field(default_factory=list)
    recent_scores: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AchievementContext:
    recent_achievements: list[str] = field(default_factory=list)
    certificates: list[str] = field(default_factory=list)
    total_achievements: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RoadmapContext:
    current_position: str = ""
    recommended_next: str = ""
    weakest_topic: str = ""
    strongest_topic: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FullContext:
    """The complete context sent to every AI request."""
    user: UserContext = field(default_factory=UserContext)
    learning: LearningContext = field(default_factory=LearningContext)
    progress: ProgressContext = field(default_factory=ProgressContext)
    activity: ActivityContext = field(default_factory=ActivityContext)
    assessment: AssessmentContext = field(default_factory=AssessmentContext)
    achievements: AchievementContext = field(default_factory=AchievementContext)
    roadmap: RoadmapContext = field(default_factory=RoadmapContext)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user.to_dict(),
            "learning": self.learning.to_dict(),
            "progress": self.progress.to_dict(),
            "activity": self.activity.to_dict(),
            "assessment": self.assessment.to_dict(),
            "achievements": self.achievements.to_dict(),
            "roadmap": self.roadmap.to_dict(),
        }

    def summary_text(self) -> str:
        """Human-readable summary for the system prompt."""
        parts = [f"Student: {self.user.username} (Level {self.progress.level}, "
                 f"{self.progress.xp} XP)"]
        if self.learning.current_lab:
            parts.append(f"Currently on: {self.learning.current_lab_title or self.learning.current_lab}")
        if self.learning.difficulty:
            parts.append(f"Difficulty: {self.learning.difficulty}")
        if self.learning.current_objective:
            parts.append(f"Current objective: {self.learning.current_objective}")
        if self.progress.labs_completed:
            parts.append(f"Completed {self.progress.labs_completed}/{self.progress.total_labs} labs")
        if self.assessment.hint_usage:
            parts.append(f"Hints used: {self.assessment.hint_usage}")
        if self.assessment.failed_objectives:
            parts.append(f"Struggling with: {', '.join(self.assessment.failed_objectives[:3])}")
        if self.achievements.total_achievements:
            parts.append(f"{self.achievements.total_achievements} achievements")
        if self.roadmap.recommended_next:
            parts.append(f"Recommended next: {self.roadmap.recommended_next}")
        return ". ".join(parts) + "."
