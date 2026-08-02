"""Recommendation models — types, skill profile, and result dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RecType(str, Enum):
    NEXT_LESSON = "next_lesson"
    NEXT_LAB = "next_lab"
    REVIEW_TOPIC = "review_topic"
    PRACTICE_LAB = "practice_lab"
    ADVANCED_TOPIC = "advanced_topic"
    BEGINNER_TOPIC = "beginner_topic"
    DAILY_GOAL = "daily_goal"
    WEEKLY_GOAL = "weekly_goal"
    CERTIFICATION_PATH = "certification_path"
    CAREER_PATH = "career_path"


@dataclass
class SkillProfile:
    strongest_topics: list[str] = field(default_factory=list)
    weakest_topics: list[str] = field(default_factory=list)
    confidence: float = 0.0          # 0–1
    recommended_difficulty: str = "Easy"
    learning_velocity: float = 0.0   # labs/week
    readiness_score: float = 0.0     # 0–1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Recommendation:
    rec_type: str = "next_lab"
    priority: int = 50               # 0–100
    title: str = ""
    slug: str = ""
    reason: str = ""
    difficulty: str = ""
    estimated_minutes: int = 0
    expected_xp: int = 0
    confidence: float = 0.5          # 0.0–1.0
    prerequisites_met: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DailyPlan:
    recommendations: list[Recommendation] = field(default_factory=list)
    review_topic: str = ""
    practice_suggestion: str = ""
    challenge: str = ""
    stretch_goal: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendations": [r.to_dict() for r in self.recommendations],
            "review_topic": self.review_topic,
            "practice_suggestion": self.practice_suggestion,
            "challenge": self.challenge,
            "stretch_goal": self.stretch_goal,
        }


@dataclass
class WeeklyPlan:
    days: dict[str, list[Recommendation]] = field(default_factory=dict)
    total_estimated_minutes: int = 0
    total_expected_xp: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "days": {d: [r.to_dict() for r in recs]
                     for d, recs in self.days.items()},
            "total_estimated_minutes": self.total_estimated_minutes,
            "total_expected_xp": self.total_expected_xp,
        }


@dataclass
class RecHistory:
    user_id: int = 0
    rec_type: str = ""
    slug: str = ""
    accepted: bool = False
    completed: bool = False
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
