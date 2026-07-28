"""Assessment services — the public API.

Every module calls these functions instead of reaching into
grading, certificate, or analytics submodules directly.

    from app.core.assessment import (
        create_assessment, complete_assessment, calculate_grade,
        calculate_xp, issue_certificate, assessment_summary,
        analytics_summary,
    )
"""

from __future__ import annotations

from typing import Any

from app.core.assessment.analytics import (
    analytics_summary as _analytics_summary,
)
from app.core.assessment.certificate import (
    CertificateRequest,
    CertificateResult,
    issue_if_passed,
)
from app.core.assessment.engine import (
    complete_assessment as _complete,
    create_assessment as _create,
    score_assessment as _score,
)
from app.core.assessment.grading import (
    GradingInput,
    GradingWeights,
    calculate_grade as _calc_grade,
)
from app.core.assessment.types import (
    AssessmentResult,
    XPConfig,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_assessment(scenario_id: int | None = None,
                      student_id: int | None = None,
                      started_at: str = "") -> AssessmentResult:
    """Create a new empty assessment."""
    return _create(scenario_id, student_id, started_at)


def complete_assessment(result: AssessmentResult,
                        raw_score: int,
                        max_score: int,
                        completed_at: str = "",
                        time_seconds: int = 0,
                        breakdown: dict[str, Any] | None = None,
                        scale: list | None = None
                        ) -> AssessmentResult:
    """Score and close an assessment in one call."""
    _score(result, raw_score, max_score, breakdown, scale)
    _complete(result, completed_at, time_seconds)
    return result


def calculate_grade(inputs: GradingInput,
                    weights: GradingWeights | None = None,
                    scale: list | None = None) -> dict[str, Any]:
    """Compute a weighted grade from raw inputs."""
    return _calc_grade(inputs, weights, scale)


def calculate_xp(config: XPConfig,
                 score_ratio: float,
                 hints_used: int = 0,
                 attempts: int = 1,
                 time_seconds: int = 0) -> dict[str, int]:
    """Calculate XP earned from an assessment."""
    return config.calculate(score_ratio, hints_used, attempts,
                            time_seconds)


def issue_certificate(certificate_slug: str,
                      student_id: int,
                      passed: bool,
                      score: int = 0,
                      grade: str = "") -> CertificateResult:
    """Issue a certificate if the student passed."""
    return issue_if_passed(CertificateRequest(
        certificate_slug=certificate_slug,
        student_id=student_id,
        score=score, grade=grade, passed=passed))


def assessment_summary(result: AssessmentResult) -> dict[str, Any]:
    """Return a display-ready summary of one assessment."""
    return result.to_dict()


def analytics_summary(results: list[AssessmentResult]) -> dict[str, Any]:
    """Compute aggregate analytics across multiple assessments."""
    return _analytics_summary(results)
