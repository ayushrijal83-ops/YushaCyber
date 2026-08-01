# Universal Leaderboard Engine

## Architecture

```
app/core/leaderboard/
├── types.py      ← LeaderboardEntry, LeaderboardPage, Season, Category,
│                    RankMetric, SeasonInfo, TIE_BREAKERS
├── ranking.py    ← sort_entries, assign_ranks, compute_trend,
│                    composite_score, paginate
├── seasons.py    ← current_seasons, season_cutoff
├── filters.py    ← filter_by_country/level/xp, apply_filters
├── models.py     ← ORM bridge: entry_from_user, all_entries
├── engine.py     ← build_leaderboard (filter→sort→paginate→rank)
└── services.py   ← get_leaderboard, get_user_rank, top_students,
                     leaderboard_summary, season_summary, export
```

## Ranking Algorithm

Primary sort by the chosen metric (default: XP). Tie-breakers in
order: XP, certificates, achievements, average score, join date.

Composite score uses configurable weights (default: XP 40%,
certificates 20%, achievements 20%, labs 10%, streak 10%).

## Seasons

All Time, Weekly, Monthly, Quarterly, Yearly. `season_cutoff()`
returns the start datetime for time-windowed queries.

## Usage

```python
from app.core.leaderboard import get_leaderboard, get_user_rank

page = get_leaderboard(metric="xp", season="monthly",
                       filters={"country": "Nepal"},
                       page=1, page_size=25, user_id=42)
rank = get_user_rank(user_id=42)
```
