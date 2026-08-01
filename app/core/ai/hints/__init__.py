"""Smart Hint Engine (YC-032.3).

    from app.core.ai.hints import (
        get_hint, hint_summary, platform_stats,
        HintResponse, HintConfig, HintStats,
    )
"""

from app.core.ai.hints.models import (  # noqa: F401
    HintConfig,
    HintResponse,
    HintStats,
)
from app.core.ai.hints.services import (  # noqa: F401
    get_hint,
    hint_summary,
    platform_stats,
)
