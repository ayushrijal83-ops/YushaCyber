"""Universal Analytics Engine (YC-031.5).

    from app.core.analytics import (
        # Types
        StudentMetrics, TrackMetrics, AssessmentMetrics,
        EngagementMetrics, AdminDashboard, Insight,
        # Services
        student_summary, student_summary_from_user,
        track_summary, assessment_summary, engagement_summary,
        admin_summary, insights_for_student, insights_for_track,
        export_analytics_json, export_analytics_csv,
    )
"""

from app.core.analytics.types import (  # noqa: F401
    AdminDashboard,
    AssessmentMetrics,
    EngagementMetrics,
    Insight,
    StudentMetrics,
    TrackMetrics,
)
from app.core.analytics.services import (  # noqa: F401
    admin_summary,
    assessment_summary,
    engagement_summary,
    export_analytics_csv,
    export_analytics_json,
    insights_for_student,
    insights_for_track,
    student_summary,
    student_summary_from_user,
    track_summary,
)
