"""Grading engine — configurable grade calculation.

Supports accuracy, completion, time bonuses, hint/attempt penalties,
and custom weights. Every module can pass its own weights or use
the defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.assessment.types import grade_from_ratio


@dataclass
class GradingWeights:
    """Configurable scoring weights (all 0.0–1.0, must sum to 1.0)."""
    accuracy: float = 0.4
    completion: float = 0.3
    time_bonus: float = 0.1
    report_quality: float = 0.2

    def validate(self) -> bool:
        return abs(sum([self.accuracy, self.completion,
                        self.time_bonus, self.report_quality]) - 1.0) < 0.01


@dataclass
class GradingInput:
    """Raw inputs for the grading engine."""
    correct: int = 0
    total: int = 0
    completed_objectives: int = 0
    total_objectives: int = 0
    time_seconds: int = 0
    time_target_seconds: int = 0
    report_score: float = 0.0   # 0.0–1.0
    hints_used: int = 0
    attempts: int = 1
    hint_penalty_pct: float = 0.02   # 2% per hint
    attempt_penalty_pct: float = 0.0  # 0% per extra attempt


def calculate_grade(inputs: GradingInput,
                    weights: GradingWeights | None = None,
                    scale: list | None = None) -> dict[str, Any]:
    """Compute a weighted grade from raw inputs."""
    w = weights or GradingWeights()

    accuracy = inputs.correct / max(1, inputs.total)
    completion = (inputs.completed_objectives
                  / max(1, inputs.total_objectives))

    time_ratio = 0.0
    if inputs.time_target_seconds > 0 and inputs.time_seconds > 0:
        time_ratio = min(1.0, max(0.0,
            1.0 - (inputs.time_seconds - inputs.time_target_seconds)
            / max(1, inputs.time_target_seconds)))
    elif inputs.time_target_seconds == 0:
        time_ratio = 1.0  # no time target = full bonus

    report = inputs.report_score

    raw = (accuracy * w.accuracy
           + completion * w.completion
           + time_ratio * w.time_bonus
           + report * w.report_quality)

    penalty = (inputs.hints_used * inputs.hint_penalty_pct
               + max(0, inputs.attempts - 1) * inputs.attempt_penalty_pct)
    final = max(0.0, min(1.0, raw - penalty))

    return {
        "raw_ratio": round(raw, 4),
        "penalty": round(penalty, 4),
        "final_ratio": round(final, 4),
        "grade": grade_from_ratio(final, scale),
        "passed": final >= 0.65,
        "breakdown": {
            "accuracy": round(accuracy, 4),
            "completion": round(completion, 4),
            "time_bonus": round(time_ratio, 4),
            "report_quality": round(report, 4),
        },
    }
