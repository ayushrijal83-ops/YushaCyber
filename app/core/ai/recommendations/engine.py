"""Recommendation engine — generates ranked recommendations.

Combines the analyzer (skill profile), rules (prerequisite/difficulty
checks), and scoring (priority ranking) into a single pipeline.
"""

from __future__ import annotations


from app.core.ai.recommendations.analyzer import analyze as build_skill_profile
from app.core.ai.recommendations.models import Recommendation, SkillProfile
from app.core.ai.recommendations.scoring import rank as score_recommendations


def generate(user, limit: int = 5) -> list[Recommendation]:
    """Generate top-N recommendations for a student."""
    profile = build_skill_profile(user)
    candidates = _collect_candidates(user, profile)
    scored = score_recommendations(candidates, profile)
    scored.sort(key=lambda r: r.priority, reverse=True)
    return scored[:limit]


def _collect_candidates(user, profile: SkillProfile
                        ) -> list[Recommendation]:
    """Gather all possible recommendations from the platform."""
    candidates: list[Recommendation] = []
    try:
        from app.labs.models import Lab, UserLabProgress
        completed_ids = {
            p.lab_id for p in
            UserLabProgress.query.filter_by(
                user_id=user.id, completed=True).all()}
        labs = Lab.query.filter_by(is_active=True).all()
        for lab in labs:
            if lab.id in completed_ids:
                continue
            # Check prerequisite.
            prereq_met = True
            if lab.prerequisite_lab_id:
                prereq_met = lab.prerequisite_lab_id in completed_ids
            candidates.append(Recommendation(
                rec_type="next_lab",
                title=lab.title,
                slug=lab.slug,
                difficulty=lab.difficulty,
                estimated_minutes=lab.estimated_minutes or 30,
                expected_xp=lab.xp_reward,
                prerequisites_met=prereq_met,
                reason=_reason_for_lab(lab, profile),
            ))
    except Exception:
        pass

    # Review suggestions for weakest topics.
    for topic in (profile.weakest_topics or [])[:2]:
        candidates.append(Recommendation(
            rec_type="review_topic",
            title=f"Review: {topic}",
            slug="",
            difficulty="Easy",
            reason=f"Your {topic} completion is below average.",
            estimated_minutes=20,
            confidence=0.7,
        ))
    return candidates


def _reason_for_lab(lab, profile: SkillProfile) -> str:
    """Generate a short reason for recommending a lab."""
    if lab.difficulty == profile.recommended_difficulty:
        return f"Matches your current level ({profile.recommended_difficulty})."
    if lab.difficulty == "Easy":
        return "A good foundation to build on."
    if lab.difficulty == "Expert":
        return "A challenge to push your skills."
    return "Next in your learning path."
