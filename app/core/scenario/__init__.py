"""Universal Scenario Engine (YC-031.1).

The single entry-point for every interactive learning module in
YushaCyber. Import from here — never reach into submodules directly.

    from app.core.scenario import (
        Scenario, Objective, Progress,
        load_scenario, complete_objective, validate_submission,
        calculate_progress, award_xp, generate_report,
    )

Backward-compatible: existing ``app/labs/`` and ``app/engines/``
code keeps working unchanged. This package wraps both into one
unified service layer.
"""

from app.core.scenario.types import (  # noqa: F401
    Difficulty,
    Grade,
    ObjectiveType,
    ReportType,
    ValidationRule,
)
from app.core.scenario.models import (  # noqa: F401
    Objective,
    Scenario,
)
from app.core.scenario.progress import Progress  # noqa: F401
from app.core.scenario.services import (  # noqa: F401
    award_xp,
    calculate_progress,
    complete_objective,
    generate_report,
    load_scenario,
    validate_submission,
)
