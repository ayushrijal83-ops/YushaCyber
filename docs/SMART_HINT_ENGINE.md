# Smart Hint Engine

## Architecture

```
app/core/ai/hints/
├── models.py      ← HintConfig, HintRequest/Response, HintRecord, HintStats
├── strategies.py  ← 5 pedagogical strategies (question, observation,
│                     comparison, concept, reflection) + prompt builder
├── rules.py       ← Rate limiting (15s), level gating, validation
├── history.py     ← Per-user per-objective hint tracking (in-memory)
├── generator.py   ← Static → AI → generic fallback chain
├── engine.py      ← Orchestrator: validate → rate-limit → level →
│                     generate → record → return
├── analytics.py   ← Platform-wide hint statistics
└── services.py    ← Public API: get_hint, hint_summary, platform_stats
```

## Hint Flow

1. Student requests hint for objective X
2. `rules.validate_request()` checks IDs
3. `rules.check_rate_limit()` enforces 15s cooldown
4. `history.current_level()` determines next level (1→2→3)
5. `generator.generate()` resolves: static hint → AI hint → generic
6. `history.record()` logs the request
7. `HintResponse` returned with level, hint text, XP penalty, remaining levels

## Hint Levels

| Level | Style | Penalty | Available to |
|---|---|---|---|
| 1 | Tiny nudge | 0 XP | All |
| 2 | Point toward evidence | −5 XP | All |
| 3 | Nearly complete guidance | −10 XP | All |
| 4 | Solution reveal | 0 XP | Admin only |

## Strategies

Each level uses a different pedagogical strategy:
- Level 1: **Question** / **Reflection** — "What evidence source records USB activity?"
- Level 2: **Observation** / **Comparison** — "Compare timestamps across two sources."
- Level 3: **Concept** / **Observation** — "USB Registry artifacts show device insertion time."

## API

```
POST /api/ai/hint
Body: {"objective_id": 123}
Response: {"level": 2, "hint": "...", "remaining_levels": 1, "xp_penalty": 5, "source": "static"}
```

## Security

- Rate limited (15s default, configurable)
- Level 4 admin-gated
- AI prompts include "NEVER reveal passwords, flags, solutions"
- `filter_for_ai()` strips sensitive fields
