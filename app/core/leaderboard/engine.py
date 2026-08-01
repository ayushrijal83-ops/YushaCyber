"""Leaderboard engine — orchestrates ranking + filtering + pagination."""

from __future__ import annotations

import json
from typing import Any

from app.core.leaderboard.filters import apply_filters
from app.core.leaderboard.ranking import (
    composite_score,
    paginate,
    sort_entries,
)
from app.core.leaderboard.types import LeaderboardEntry, LeaderboardPage


def build_leaderboard(entries: list[LeaderboardEntry],
                      metric: str = "xp",
                      season: str = "all_time",
                      filters: dict[str, Any] | None = None,
                      page: int = 1,
                      page_size: int = 25,
                      user_id: int | None = None
                      ) -> LeaderboardPage:
    """Full pipeline: filter → sort → paginate → find user rank."""
    if filters:
        entries = apply_filters(entries, filters)
    if metric == "composite":
        for e in entries:
            e.score = composite_score(e)
        entries = sort_entries(entries, "score")
    else:
        entries = sort_entries(entries, metric)
    user_rank = None
    if user_id:
        for e in entries:
            if e.user_id == user_id:
                user_rank = e.rank
                break
    paged = paginate(entries, page, page_size)
    return LeaderboardPage(
        entries=paged, total=len(entries),
        page=page, page_size=page_size,
        season=season, metric=metric,
        user_rank=user_rank)


def export_json(entries: list[LeaderboardEntry]) -> str:
    return json.dumps([e.to_dict() for e in entries], indent=2)


def export_csv(entries: list[LeaderboardEntry]) -> str:
    from app.core.analytics.engine import export_csv as _csv
    return _csv([e.to_dict() for e in entries])
