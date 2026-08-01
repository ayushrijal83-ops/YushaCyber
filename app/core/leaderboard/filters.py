"""Filters — filter leaderboard entries by various criteria."""

from __future__ import annotations

from typing import Any

from app.core.leaderboard.types import LeaderboardEntry


def filter_by_country(entries: list[LeaderboardEntry],
                      country: str) -> list[LeaderboardEntry]:
    country = country.strip().lower()
    return [e for e in entries
            if e.country.strip().lower() == country]


def filter_by_min_level(entries: list[LeaderboardEntry],
                        min_level: int) -> list[LeaderboardEntry]:
    return [e for e in entries if e.level >= min_level]


def filter_by_min_xp(entries: list[LeaderboardEntry],
                     min_xp: int) -> list[LeaderboardEntry]:
    return [e for e in entries if e.xp >= min_xp]


def apply_filters(entries: list[LeaderboardEntry],
                  filters: dict[str, Any]) -> list[LeaderboardEntry]:
    """Apply a dict of filters."""
    result = list(entries)
    if filters.get("country"):
        result = filter_by_country(result, filters["country"])
    if filters.get("min_level"):
        result = filter_by_min_level(result, int(filters["min_level"]))
    if filters.get("min_xp"):
        result = filter_by_min_xp(result, int(filters["min_xp"]))
    return result
