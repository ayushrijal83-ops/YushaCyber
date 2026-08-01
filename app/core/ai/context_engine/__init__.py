"""Intelligent Context Engine (YC-032.2).

    from app.core.ai.context_engine import (
        get_context, get_context_dict, get_context_summary,
        get_learning_profile, filter_for_ai,
        on_page_visit, on_lab_start, on_lab_complete,
        on_objective_complete, on_hint_used, on_answer_submitted,
    )
"""

from app.core.ai.context_engine.services import (  # noqa: F401
    filter_for_ai,
    get_context,
    get_context_dict,
    get_context_summary,
    get_learning_profile,
)
from app.core.ai.context_engine.session import (  # noqa: F401
    on_answer_submitted,
    on_hint_used,
    on_lab_complete,
    on_lab_start,
    on_objective_complete,
    on_page_visit,
)
