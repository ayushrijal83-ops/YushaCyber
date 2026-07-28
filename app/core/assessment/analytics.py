"""Analytics engine — reusable assessment statistics.

Generates aggregate stats from a list of AssessmentResult objects.
Works with in-memory data — no database queries. Any module that
collects results can compute analytics through this.
"""

from __future__ import annotations

from typing import Any

from app.core.assessment.types import AssessmentResult


def analytics_summary(results: list[AssessmentResult]) -> dict[str, Any]:
    """Compute aggregate statistics from assessment results."""
    if not results:
        return {
            "count": 0,
            "average_score": 0.0,
            "highest_score": 0,
            "lowest_score": 0,
            "pass_rate": 0.0,
            "completion_rate": 0.0,
            "average_time_seconds": 0,
            "total_xp_earned": 0,
            "grade_distribution": {},
        }

    scores = [r.final_score for r in results]
    passed = sum(1 for r in results if r.passed)
    completed = sum(1 for r in results if r.completed_at)
    times = [r.time_taken_seconds for r in results
             if r.time_taken_seconds and r.time_taken_seconds > 0]

    grade_dist: dict[str, int] = {}
    for r in results:
        grade_dist[r.grade] = grade_dist.get(r.grade, 0) + 1

    return {
        "count": len(results),
        "average_score": round(sum(scores) / len(scores), 1),
        "highest_score": max(scores),
        "lowest_score": min(scores),
        "pass_rate": round(passed / len(results), 2),
        "completion_rate": round(completed / len(results), 2),
        "average_time_seconds": (
            round(sum(times) / len(times)) if times else 0),
        "total_xp_earned": sum(r.xp_earned for r in results),
        "grade_distribution": grade_dist,
    }
