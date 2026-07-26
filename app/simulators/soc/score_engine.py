"""Score engine for Incident Response (YC-030.3).

Aggregates decision score + report quality + evidence usage +
timeline accuracy into a single grade.

Reusable — any future IR scenario calls ``compute_final_score``.
"""

from __future__ import annotations

from typing import Any

from app.simulators.soc.decision_engine import score_decisions

REPORT_SECTIONS = (
    "executive summary", "incident timeline", "evidence",
    "root cause", "containment", "recovery", "recommendations",
)


def report_quality(report: str) -> dict[str, Any]:
    """Grade the report text."""
    text = (report or "").strip().lower()
    length_ok = len(text) >= 150
    sections_hit = sum(1 for s in REPORT_SECTIONS if s in text)
    sections_ok = sections_hit >= 4
    return {
        "length_ok": length_ok,
        "sections_hit": sections_hit,
        "sections_ok": sections_ok,
        "report_score": min(30, sections_hit * 5 + (10 if length_ok else 0)),
    }


def compute_final_score(
        decisions: list[dict[str, Any]],
        report: str,
        phases_completed: int,
        total_phases: int = 5,
        hints_used: int = 0) -> dict[str, Any]:
    """Aggregate everything into a single grade.

    Returns ``{total, max, ratio, rating, breakdown}``.
    """
    dec = score_decisions(decisions)
    rpt = report_quality(report)

    phase_score = int((phases_completed / max(1, total_phases)) * 30)
    hint_penalty = hints_used * 5
    total = max(0, dec["total_points"] + rpt["report_score"]
                + phase_score - hint_penalty)
    max_score = (len(decisions) * 10) + 30 + 30  # decisions + report + phases
    ratio = total / max(1, max_score)

    if ratio >= 0.9:
        rating = "Excellent"
    elif ratio >= 0.75:
        rating = "Good"
    else:
        rating = "Needs Improvement"

    return {
        "total": total,
        "max": max_score,
        "ratio": round(ratio, 2),
        "rating": rating,
        "breakdown": {
            "decisions": dec,
            "report": rpt,
            "phases": {"completed": phases_completed,
                       "total": total_phases,
                       "score": phase_score},
            "hints": {"used": hints_used,
                      "penalty": hint_penalty},
        },
    }
