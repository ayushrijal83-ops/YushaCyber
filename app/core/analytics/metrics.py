"""Metrics — pure computation helpers for analytics.

All functions take raw data (lists/dicts) and return computed values.
No database access — the caller fetches data and passes it in.
"""

from __future__ import annotations



def completion_rate(completed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(completed / total, 2)


def average(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def grade_from_scores(scores: list[float],
                      max_score: float = 100.0) -> str:
    if not scores or max_score <= 0:
        return ""
    avg_ratio = average(scores) / max_score
    if avg_ratio >= 0.93:
        return "A"
    if avg_ratio >= 0.85:
        return "B"
    if avg_ratio >= 0.75:
        return "C"
    if avg_ratio >= 0.65:
        return "D"
    return "F"


def grade_distribution(grades: list[str]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for g in grades:
        dist[g] = dist.get(g, 0) + 1
    return dist


def score_distribution(scores: list[float],
                       buckets: int = 5,
                       max_score: float = 100.0) -> dict[str, int]:
    """Bucket scores into ranges like 0-20, 20-40, etc."""
    step = max_score / buckets
    dist: dict[str, int] = {}
    for i in range(buckets):
        lo = int(step * i)
        hi = int(step * (i + 1))
        label = f"{lo}-{hi}"
        dist[label] = sum(1 for s in scores if lo <= s < hi)
    # Include max in last bucket.
    if scores:
        last_label = list(dist.keys())[-1]
        dist[last_label] += sum(1 for s in scores if s == max_score)
    return dist


def difficulty_distribution(
        difficulties: list[str]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for d in difficulties:
        dist[d] = dist.get(d, 0) + 1
    return dist


def pass_fail_rates(passed: int,
                    total: int) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    pr = round(passed / total, 2)
    return pr, round(1.0 - pr, 2)
