"""Ranking — pure computation helpers for sorting and tie-breaking."""

from __future__ import annotations


from app.core.leaderboard.types import LeaderboardEntry


def sort_entries(entries: list[LeaderboardEntry],
                 metric: str = "xp") -> list[LeaderboardEntry]:
    """Sort entries by the primary metric, then tie-breakers."""
    def sort_key(e: LeaderboardEntry):
        primary = -getattr(e, metric, getattr(e, "xp", 0))
        return (primary, -e.xp, -e.certificates,
                -e.achievements, -e.score)
    entries.sort(key=sort_key)
    for i, entry in enumerate(entries, 1):
        entry.rank = i
    return entries


def assign_ranks(entries: list[LeaderboardEntry]
                 ) -> list[LeaderboardEntry]:
    """Assign ranks 1..N to pre-sorted entries."""
    for i, e in enumerate(entries, 1):
        e.rank = i
    return entries


def compute_trend(current_rank: int,
                  previous_rank: int | None) -> str:
    """Compute ▲ ▼ ➜ trend indicator."""
    if previous_rank is None:
        return "➜"
    if current_rank < previous_rank:
        return "▲"
    if current_rank > previous_rank:
        return "▼"
    return "➜"


def composite_score(entry: LeaderboardEntry,
                    weights: dict[str, float] | None = None
                    ) -> float:
    """Compute a weighted composite score."""
    w = weights or {
        "xp": 0.4, "certificates": 0.2,
        "achievements": 0.2, "completed_labs": 0.1,
        "streak": 0.1,
    }
    score = 0.0
    for key, weight in w.items():
        score += getattr(entry, key, 0) * weight
    return round(score, 1)


def paginate(entries: list[LeaderboardEntry],
             page: int = 1,
             page_size: int = 25) -> list[LeaderboardEntry]:
    """Return one page of entries."""
    start = (page - 1) * page_size
    return entries[start:start + page_size]
