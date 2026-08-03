"""AI Analytics & Instructor Dashboard (YC-032.5).

    from app.core.ai.analytics import (
        dashboard_metrics, dashboard_dict,
        get_report, get_charts, export_data, refresh,
    )
"""

from app.core.ai.analytics.services import (  # noqa: F401
    dashboard_dict,
    dashboard_metrics,
    export_data,
    get_charts,
    get_report,
    refresh,
)
