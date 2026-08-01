"""Leaderboard services — the public API."""

from __future__ import annotations

from typing import Any

from app.core.leaderboard.engine import build_leaderboard, export_csv, export_json
from app.core.leaderboard.models import all_entries
from app.core.leaderboard.seasons import current_seasons
from app.core.leaderboard.types import LeaderboardEntry, LeaderboardPage


def get_leaderboard(metric: str = "xp",
                    season: str = "all_time",
                    filters: dict[str, Any] | None = None,
                    page: int = 1,
                    page_size: int = 25,
                    user_id: int | None = None
                    ) -> LeaderboardPage:
    """Full leaderboard with ranking, filtering, pagination."""
    entries = all_entries()
    return build_leaderboard(entries, metric, season, filters,
                             page, page_size, user_id)


def get_user_rank(user_id: int,
                  metric: str = "xp") -> int | None:
    """Get a single user's rank."""
    page = get_leaderboard(metric=metric, user_id=user_id,
                           page_size=9999)
    return page.user_rank


def top_students(limit: int = 10,
                 metric: str = "xp") -> list[LeaderboardEntry]:
    """Top N students by metric."""
    page = get_leaderboard(metric=metric, page_size=limit)
    return page.entries


def leaderboard_summary(user_id: int | None = None
                        ) -> dict[str, Any]:
    """Quick summary for dashboard widgets."""
    page = get_leaderboard(user_id=user_id, page_size=5)
    return {
        "top_5": [e.to_dict() for e in page.entries],
        "total_students": page.total,
        "user_rank": page.user_rank,
    }


def season_summary() -> list[dict[str, Any]]:
    """Return all active seasons with metadata."""
    return [s.to_dict() for s in current_seasons()]


def export_leaderboard_json(metric: str = "xp") -> str:
    return export_json(all_entries())


def export_leaderboard_csv(metric: str = "xp") -> str:
    return export_csv(all_entries())
