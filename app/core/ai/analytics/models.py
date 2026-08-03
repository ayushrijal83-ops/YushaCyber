"""AI analytics models — metric dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AIUsageMetrics:
    total_conversations: int = 0
    messages_today: int = 0
    messages_week: int = 0
    messages_month: int = 0
    avg_response_ms: int = 0
    avg_tokens: int = 0
    provider: str = ""
    model: str = ""
    most_active_students: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StudentAnalytics:
    total_active: int = 0
    avg_xp: int = 0
    avg_level: int = 1
    completion_rate: float = 0.0
    labs_completed: int = 0
    avg_study_minutes: int = 0
    students_needing_help: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HintAnalytics:
    total_requested: int = 0
    level_distribution: dict[int, int] = field(default_factory=dict)
    most_difficult_objectives: list[dict[str, Any]] = field(default_factory=list)
    hint_success_rate: float = 0.0
    xp_lost: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationAnalytics:
    total_generated: int = 0
    accepted: int = 0
    ignored: int = 0
    completion_rate: float = 0.0
    weakest_topics: list[str] = field(default_factory=list)
    strongest_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LabAnalytics:
    total_labs: int = 0
    completion_rate: float = 0.0
    avg_attempts: float = 0.0
    most_difficult: list[dict[str, Any]] = field(default_factory=list)
    most_completed: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AIHealthMetrics:
    provider: str = ""
    model: str = ""
    status: str = "unknown"
    avg_latency_ms: int = 0
    error_rate: float = 0.0
    cache_hit_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardData:
    """Complete dashboard payload."""
    ai_usage: AIUsageMetrics = field(default_factory=AIUsageMetrics)
    students: StudentAnalytics = field(default_factory=StudentAnalytics)
    hints: HintAnalytics = field(default_factory=HintAnalytics)
    recommendations: RecommendationAnalytics = field(
        default_factory=RecommendationAnalytics)
    labs: LabAnalytics = field(default_factory=LabAnalytics)
    health: AIHealthMetrics = field(default_factory=AIHealthMetrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ai_usage": self.ai_usage.to_dict(),
            "students": self.students.to_dict(),
            "hints": self.hints.to_dict(),
            "recommendations": self.recommendations.to_dict(),
            "labs": self.labs.to_dict(),
            "health": self.health.to_dict(),
        }
