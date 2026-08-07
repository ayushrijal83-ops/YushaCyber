"""Interactive Cyber Lab Engine (YC-034.0).

    from app.core.lab_engine import (
        # Services
        start_lab, submit_objective, use_hint, reset_lab,
        get_session, get_ai_context, available_labs,
        # Registration
        register_lab, register_workspace,
        # Types
        LabDef, LabObjectiveDef, Workspace, LabType,
    )
"""

from app.core.lab_engine.registry import (  # noqa: F401
    register_lab,
    register_workspace,
)
from app.core.lab_engine.services import (  # noqa: F401
    available_labs,
    available_types,
    get_ai_context,
    get_session,
    reset_lab,
    start_lab,
    submit_objective,
    use_hint,
)
from app.core.lab_engine.types import (  # noqa: F401
    LabDef,
    LabObjectiveDef,
    LabType,
    Workspace,
)
