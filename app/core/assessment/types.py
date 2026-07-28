"""Assessment types — enums, grade scales, and dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CertificateType(str, Enum):
    COMPLETION = "completion"
    TRACK = "track"
    ASSESSMENT = "assessment"
    PROFESSIONAL = "professional"


# ---------------------------------------------------------------------------
# Grade scales
# ---------------------------------------------------------------------------
@dataclass
class GradeThreshold:
    label: str
    min_ratio: float  # 0.0 – 1.0


DEFAULT_GRADE_SCALE: list[GradeThreshold] = [
    GradeThreshold("A+", 0.97),
    GradeThreshold("A",  0.93),
    GradeThreshold("B",  0.85),
    GradeThreshold("C",  0.75),
    GradeThreshold("D",  0.65),
    GradeThreshold("F",  0.00),
]

PASS_FAIL_SCALE: list[GradeThreshold] = [
    GradeThreshold("Excellent",         0.90),
    GradeThreshold("Pass",              0.65),
    GradeThreshold("Needs Improvement", 0.40),
    GradeThreshold("Fail",              0.00),
]


def grade_from_ratio(ratio: float,
                     scale: list[GradeThreshold] | None = None
                     ) -> str:
    """Return the highest grade whose threshold the ratio meets."""
    scale = scale or DEFAULT_GRADE_SCALE
    for threshold in scale:
        if ratio >= threshold.min_ratio:
            return threshold.label
    return scale[-1].label if scale else "F"


# ---------------------------------------------------------------------------
# Assessment result dataclass
# ---------------------------------------------------------------------------
@dataclass
class AssessmentResult:
    """In-memory assessment result — NOT an ORM model."""

    scenario_id: int | None = None
    student_id: int | None = None
    started_at: str = ""
    completed_at: str = ""
    raw_score: int = 0
    max_score: int = 0
    final_score: int = 0
    grade: str = ""
    xp_earned: int = 0
    bonus_xp: int = 0
    time_taken_seconds: int = 0
    attempts: int = 0
    hints_used: int = 0
    certificate_issued: bool = False
    passed: bool = False
    breakdown: dict[str, Any] = field(default_factory=dict)

    @property
    def ratio(self) -> float:
        return self.final_score / max(1, self.max_score)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        d = asdict(self)
        d["ratio"] = self.ratio
        return d


# ---------------------------------------------------------------------------
# XP calculation config
# ---------------------------------------------------------------------------
@dataclass
class XPConfig:
    """Configurable XP calculation weights."""

    base_xp: int = 0
    difficulty_multiplier: float = 1.0
    perfect_bonus: int = 0       # extra XP for 100% score
    speed_bonus_max: int = 0     # max XP for fast completion
    speed_threshold_seconds: int = 0  # complete under this for speed bonus
    hint_penalty_per: int = 5    # XP deducted per hint
    attempt_penalty_per: int = 0  # XP deducted per extra attempt

    def calculate(self,
                  score_ratio: float,
                  hints_used: int = 0,
                  attempts: int = 1,
                  time_seconds: int = 0) -> dict[str, int]:
        base = int(self.base_xp * self.difficulty_multiplier)
        perfect = self.perfect_bonus if score_ratio >= 1.0 else 0
        speed = 0
        if (self.speed_bonus_max > 0
                and self.speed_threshold_seconds > 0
                and 0 < time_seconds <= self.speed_threshold_seconds):
            speed = self.speed_bonus_max
        hint_pen = hints_used * self.hint_penalty_per
        attempt_pen = max(0, attempts - 1) * self.attempt_penalty_per
        total = max(0, base + perfect + speed - hint_pen - attempt_pen)
        return {
            "base": base,
            "perfect_bonus": perfect,
            "speed_bonus": speed,
            "hint_penalty": hint_pen,
            "attempt_penalty": attempt_pen,
            "total": total,
        }
