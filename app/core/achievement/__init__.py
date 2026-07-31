"""Universal Achievement Framework (YC-031.4).

    from app.core.achievement import (
        # Types
        AchievementDef, Badge, Rarity, UnlockCondition,
        RARITY_COLORS, AchievementSummary,
        # Models
        achievement_from_orm, achievement_from_dict,
        # Badges
        generate_badge, generate_badges,
        # Rules
        available_rules, evaluate_rule,
        # Services
        register_achievement, check_unlock_for_user,
        award, award_multiple, list_student_achievements,
        achievement_summary,
    )
"""

from app.core.achievement.types import (  # noqa: F401
    AchievementDef,
    Badge,
    Rarity,
    RARITY_COLORS,
    UnlockCondition,
)
from app.core.achievement.models import (  # noqa: F401
    achievement_from_dict,
    achievement_from_orm,
    badge_from_achievement,
)
from app.core.achievement.badges import (  # noqa: F401
    generate_badge,
    generate_badges,
)
from app.core.achievement.rules import (  # noqa: F401
    available_rules,
    evaluate_rule,
)
from app.core.achievement.services import (  # noqa: F401
    achievement_summary,
    all_registered,
    award,
    award_multiple,
    check_unlock_for_user,
    get_registered,
    list_student_achievements,
    register_achievement,
)
