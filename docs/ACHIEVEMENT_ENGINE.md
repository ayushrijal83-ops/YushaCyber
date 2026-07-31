# Universal Achievement Framework

## Architecture

```
app/core/achievement/
├── __init__.py      ← Public API exports
├── types.py         ← AchievementDef, Badge, UnlockResult, Rarity,
│                       UnlockCondition, RARITY_COLORS
├── models.py        ← achievement_from_dict(), achievement_from_orm(),
│                       badge_from_achievement()
├── engine.py        ← check_unlock(), check_multiple(),
│                       generate_badge(), achievement_summary()
├── rules.py         ← Rule registry + evaluate_rule/evaluate_all
│                       Built-in: lab_completed, xp_milestone,
│                       level_milestone, perfect_score, speed_run,
│                       certificate_earned, custom
├── badges.py        ← Badge display helpers
└── services.py      ← Public API: register_achievement(),
                        check_unlock_for_user(), award(),
                        award_multiple(), list_student_achievements(),
                        achievement_summary()
```

## Rule System

Each achievement has a list of requirements. Every requirement is a
dict with `type` and `value`. The rule engine evaluates all of them
(AND logic). An achievement with no requirements auto-unlocks.

Built-in rules:

| Rule Type | Value | Metric Key | Example |
|---|---|---|---|
| lab_completed | count | lab_completed | Complete 5 labs |
| soc_lab_completed | count | soc_lab_completed | Complete 8 SOC labs |
| xp_milestone | amount | total_xp | Earn 1000 XP |
| level_milestone | level | level | Reach level 10 |
| perfect_score | 1 | perfect_scores | Get a perfect score |
| speed_run | seconds | fastest_time | Complete under 300s |
| certificate_earned | slug | certificates | Earn a certificate |
| custom | callback | (varies) | Custom function |

## Rarity

Five tiers with colors: Common (#8b95a5), Rare (#3b82f6),
Epic (#a855f7), Legendary (#f59e0b), Mythic (#ef4444).

## Extension Guide

### Registering a new achievement

```python
from app.core.achievement import register_achievement

register_achievement({
    "slug": "speed-demon",
    "title": "Speed Demon",
    "description": "Complete any lab in under 5 minutes.",
    "rarity": "epic",
    "xp_reward": 100,
    "requirements": [{"type": "speed_run", "value": 300}],
})
```

### Adding a custom rule

Add to `rules.py`:

```python
@register_rule("custom_rule_name")
def _my_rule(value: Any, metrics: dict) -> bool:
    return metrics.get("my_metric", 0) >= value
```

### Checking unlocks

```python
from app.core.achievement import check_unlock_for_user

result = check_unlock_for_user(achievement_def, user_metrics)
if result.unlocked:
    print(f"Unlocked! +{result.xp_awarded} XP")
```

## Migration

Existing `app/achievement/` keeps working. The core framework
wraps it — `achievement_from_orm()` converts ORM rows to
`AchievementDef` dataclasses. `award()` delegates to the
existing `unlock_achievement()` service.
