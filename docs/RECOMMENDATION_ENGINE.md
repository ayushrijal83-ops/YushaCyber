# Personalized Learning Recommendation Engine

## Architecture

```
app/core/ai/recommendations/
├── models.py    ← Recommendation, DailyPlan, WeeklyPlan, SkillProfile,
│                   RecommendationType enum
├── analyzer.py  ← analyze_student() — builds SkillProfile from ORM
├── engine.py    ← generate_recommendations() — next labs, review topics
├── scoring.py   ← rank_recommendations() — priority-based sorting
├── planner.py   ← daily_plan(), weekly_plan() — time-distributed plans
├── rules.py     ← prerequisite checking, locked-content filtering
├── history.py   ← Tracks accepted/ignored/completed recommendations
└── services.py  ← Public API: get_recommendations, get_daily_plan,
                    get_weekly_plan, get_skill_profile
```

## Recommendation Flow

1. `analyze_student(user)` → `SkillProfile` (strengths, weaknesses, velocity)
2. `generate_recommendations(user, profile)` → candidate list
3. `rank_recommendations(candidates)` → sorted by priority
4. `rules.filter_locked(candidates)` → remove prerequisites-not-met
5. Return top N recommendations

## Scoring Algorithm

Each recommendation gets a priority (0–100) based on:
- **Roadmap position** — next uncompleted lab gets highest priority
- **Weakness compensation** — weak topics get review recommendations
- **Difficulty match** — matches the student's current level
- **Confidence** — how sure the engine is this is the right next step

## API

```
GET /api/ai/recommendations → {recommendations: [...]}
```

## Weekly Plan

Distributes recommendations across 7 days based on a daily time budget (default 60 min). Each day gets lessons + labs + practice until the budget is filled.

## Extension

Add a new recommendation type by adding to `RecommendationType` enum and generating candidates in `engine.py`.
