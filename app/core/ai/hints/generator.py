"""Hint generator — resolves hints via static → AI → generic."""

from __future__ import annotations


from app.core.ai.hints.models import HintResponse
from app.core.ai.hints.strategies import build_hint_prompt


def generate(objective, level: int,
             previous_hints: list[str],
             lab_title: str = "",
             difficulty: str = "",
             attempts: int = 0,
             use_ai: bool = True) -> HintResponse:
    """Generate a hint for the given level.

    Priority: static hint → AI hint → generic guidance.
    """
    # 1. Static hints from LabObjective.
    static = _get_static_hint(objective, level)
    if static:
        return HintResponse(
            level=level, hint=static, source="static",
            remaining_levels=max(0, 3 - level))

    # 2. AI-generated hint.
    if use_ai:
        ai_hint = _generate_ai_hint(
            level, objective.title or "",
            lab_title, difficulty,
            previous_hints, attempts)
        if ai_hint:
            return HintResponse(
                level=level, hint=ai_hint, source="ai",
                remaining_levels=max(0, 3 - level))

    # 3. Generic fallback.
    generic = _generic_hint(level)
    return HintResponse(
        level=level, hint=generic, source="generic",
        remaining_levels=max(0, 3 - level))


def _get_static_hint(objective, level: int) -> str:
    """Read hint1/hint2/hint3 from the LabObjective."""
    hints = {
        1: getattr(objective, "hint1", None),
        2: getattr(objective, "hint2", None),
        3: getattr(objective, "hint3", None),
    }
    return (hints.get(level) or "").strip()


def _generate_ai_hint(level: int, objective_title: str,
                      lab_title: str, difficulty: str,
                      previous_hints: list[str],
                      attempts: int) -> str:
    """Generate via CyberMentor AI (if enabled + available)."""
    try:
        from app.core.ai.config import is_enabled
        if not is_enabled():
            return ""
        prompt = build_hint_prompt(
            level, objective_title, lab_title, difficulty,
            previous_hints, attempts)
        from app.core.ai.manager import get_manager
        from app.core.ai.types import Message
        response = get_manager().chat([
            Message(role="system",
                    content="You are CyberMentor's hint generator. "
                            "Generate educational hints that guide "
                            "without revealing answers."),
            Message(role="user", content=prompt),
        ])
        if response.content and "[AI Error]" not in response.content:
            return response.content.strip()
    except Exception:
        pass
    return ""


def _generic_hint(level: int) -> str:
    """Generic fallback hints."""
    generic = {
        1: "Take another look at the evidence. Something may not be what it seems.",
        2: "Try comparing different evidence sources — timestamps and patterns can reveal connections.",
        3: "Review all the evidence carefully. The answer is in the data you've already seen.",
    }
    return generic.get(level, "Keep investigating — you're on the right track.")
