"""Assessment engine — core lifecycle for any assessment.

Stateless functions that create, score, and complete assessments.
These wrap the existing scoring engines (SOC score_engine,
assessment_engine, hunt_engine) into a unified interface.
"""

from __future__ import annotations

from typing import Any

from app.core.assessment.types import AssessmentResult, grade_from_ratio


def create_assessment(scenario_id: int | None = None,
                      student_id: int | None = None,
                      started_at: str = "") -> AssessmentResult:
    """Create a fresh, empty assessment result."""
    return AssessmentResult(
        scenario_id=scenario_id,
        student_id=student_id,
        started_at=started_at,
    )


def score_assessment(result: AssessmentResult,
                     raw_score: int,
                     max_score: int,
                     breakdown: dict[str, Any] | None = None,
                     scale: list | None = None) -> AssessmentResult:
    """Apply a raw score and compute grade."""
    result.raw_score = raw_score
    result.max_score = max_score
    result.final_score = max(0, raw_score)
    result.breakdown = breakdown or {}
    result.grade = grade_from_ratio(result.ratio, scale)
    result.passed = result.ratio >= 0.65
    return result


def complete_assessment(result: AssessmentResult,
                        completed_at: str = "",
                        time_seconds: int = 0) -> AssessmentResult:
    """Mark an assessment as complete."""
    result.completed_at = completed_at
    result.time_taken_seconds = time_seconds
    return result
