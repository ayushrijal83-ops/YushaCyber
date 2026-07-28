"""Assessment models — bridges between ORM and the assessment API.

These are builder functions, not ORM models. They construct
``AssessmentResult`` dataclasses from existing ORM data.
"""

from __future__ import annotations

from typing import Any

from app.core.assessment.types import AssessmentResult


def result_from_state(state: dict[str, Any],
                      score: dict[str, Any],
                      scenario_id: int | None = None,
                      student_id: int | None = None) -> AssessmentResult:
    """Build an AssessmentResult from simulator state + a score dict."""
    return AssessmentResult(
        scenario_id=scenario_id,
        student_id=student_id,
        raw_score=score.get("total", 0),
        max_score=score.get("max", 0),
        final_score=score.get("total", 0),
        grade=score.get("grade") or score.get("rating") or "",
        hints_used=int(state.get("hints_used") or 0),
        attempts=int(state.get("attempts") or 1),
        passed=score.get("grade", "") in ("Excellent", "Good",
                                           "Pass", "A+", "A", "B"),
        breakdown=score.get("breakdown") or {},
    )


def result_from_lab_progress(user, lab, score_dict: dict[str, Any] | None = None) -> AssessmentResult:
    """Build an AssessmentResult from a Lab + user progress."""
    from app.labs import lab_services
    done = lab_services._completed_objective_ids(user, lab)
    total = len(lab.objectives)
    completed = len(done)
    ratio = completed / max(1, total)
    from app.core.assessment.types import grade_from_ratio
    grade = grade_from_ratio(ratio)
    return AssessmentResult(
        scenario_id=lab.id,
        student_id=user.id,
        raw_score=completed,
        max_score=total,
        final_score=completed,
        grade=grade,
        xp_earned=lab.xp_reward,
        passed=ratio >= 0.65,
        breakdown=score_dict or {},
    )
