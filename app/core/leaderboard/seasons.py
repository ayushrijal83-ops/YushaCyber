"""Seasons — time-window definitions for leaderboard periods."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.leaderboard.types import SeasonInfo


def current_seasons() -> list[SeasonInfo]:
    """Return metadata for all active seasons."""
    now = datetime.now(timezone.utc)
    return [
        SeasonInfo("all_time", "All Time", "", "", True),
        SeasonInfo("weekly", "This Week",
                   (now - timedelta(days=now.weekday())).isoformat(),
                   now.isoformat(), True),
        SeasonInfo("monthly", "This Month",
                   now.replace(day=1).isoformat(),
                   now.isoformat(), True),
        SeasonInfo("yearly", f"{now.year}",
                   now.replace(month=1, day=1).isoformat(),
                   now.isoformat(), True),
    ]


def season_cutoff(season: str) -> datetime | None:
    """Return the start datetime for a season window, or None."""
    now = datetime.now(timezone.utc)
    if season == "weekly":
        return now - timedelta(days=now.weekday())
    if season == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0)
    if season == "quarterly":
        q_month = ((now.month - 1) // 3) * 3 + 1
        return now.replace(month=q_month, day=1, hour=0, minute=0, second=0)
    if season == "yearly":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0)
    return None  # all_time
