"""Scoring engine — computes priority for each recommendation."""

from __future__ import annotations

from app.core.ai.recommendations.models import Recommendation, SkillProfile


def score_recommendation(rec: Recommendation,
                         profile: SkillProfile) -> Recommendation:
    """Adjust priority based on the student's skill profile."""
    base = rec.priority
    # Boost weak-topic reviews.
    if rec.rec_type == "review_topic":
        if any(t.lower() in rec.title.lower()
               for t in profile.weakest_topics):
            base += 20
    # Boost next-lab if prerequisites met.
    if rec.rec_type == "next_lab" and rec.prerequisites_met:
        base += 10
    # Penalize too-hard recommendations.
    diff_order = {"Easy": 1, "Medium": 2, "Hard": 3, "Expert": 4}
    rec_diff = diff_order.get(rec.difficulty, 2)
    profile_diff = diff_order.get(profile.recommended_difficulty, 2)
    if rec_diff > profile_diff + 1:
        base -= 15
    # Cap.
    rec.priority = max(0, min(100, base))
    return rec


def rank(recommendations: list[Recommendation],
         profile: SkillProfile) -> list[Recommendation]:
    """Score and rank all recommendations."""
    scored = [score_recommendation(r, profile)
              for r in recommendations]
    scored.sort(key=lambda r: r.priority, reverse=True)
    return scored
