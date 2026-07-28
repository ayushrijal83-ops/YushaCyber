"""Universal Assessment Engine (YC-031.2).

The single entry-point for grading, certification, XP calculation,
and analytics across every learning module in YushaCyber.

    from app.core.assessment import (
        # Types
        AssessmentResult, XPConfig, GradeThreshold,
        CertificateType, GradingInput, GradingWeights,
        # Grade helpers
        grade_from_ratio, DEFAULT_GRADE_SCALE, PASS_FAIL_SCALE,
        # Services
        create_assessment, complete_assessment,
        calculate_grade, calculate_xp,
        issue_certificate, assessment_summary,
        analytics_summary,
    )

Backward-compatible: existing ``app/certificates/``,
``app/achievement/``, ``app/dashboard/services.award_xp`` keep
working unchanged. This package wraps them into one unified API.
"""

from app.core.assessment.types import (  # noqa: F401
    AssessmentResult,
    CertificateType,
    DEFAULT_GRADE_SCALE,
    GradeThreshold,
    PASS_FAIL_SCALE,
    XPConfig,
    grade_from_ratio,
)
from app.core.assessment.grading import (  # noqa: F401
    GradingInput,
    GradingWeights,
)
from app.core.assessment.services import (  # noqa: F401
    analytics_summary,
    assessment_summary,
    calculate_grade,
    calculate_xp,
    complete_assessment,
    create_assessment,
    issue_certificate,
)
