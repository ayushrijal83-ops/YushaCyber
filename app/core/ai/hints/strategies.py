"""Hint strategies — pedagogical approaches for generating hints."""

from __future__ import annotations


STRATEGIES = {
    "question": "Ask a guiding question that leads the student to discover the answer.",
    "observation": "Point out a detail the student may have overlooked.",
    "comparison": "Suggest comparing two evidence sources or data points.",
    "concept": "Remind the student of a relevant cybersecurity concept.",
    "reflection": "Ask the student to re-examine their assumptions.",
}

LEVEL_STRATEGIES: dict[int, list[str]] = {
    1: ["question", "reflection"],
    2: ["observation", "comparison"],
    3: ["concept", "observation"],
}


def strategy_for_level(level: int) -> str:
    """Pick the primary strategy for a hint level."""
    strategies = LEVEL_STRATEGIES.get(level, ["observation"])
    return strategies[0]


def strategy_prompt(strategy: str) -> str:
    """Return the instructional prompt for a strategy."""
    return STRATEGIES.get(strategy,
                          "Guide the student without revealing the answer.")


def build_hint_prompt(level: int, objective_title: str,
                      lab_title: str, difficulty: str,
                      previous_hints: list[str],
                      attempts: int = 0) -> str:
    """Build a prompt for AI-generated hints."""
    strategy = strategy_for_level(level)
    instruction = strategy_prompt(strategy)

    parts = [
        f"Generate a Level {level} hint for a cybersecurity lab.",
        f"Lab: {lab_title} (Difficulty: {difficulty})",
        f"Objective: {objective_title}",
        f"Strategy: {instruction}",
        f"Student has made {attempts} attempt(s).",
    ]
    if previous_hints:
        parts.append("Previous hints given:")
        for i, h in enumerate(previous_hints, 1):
            parts.append(f"  Level {i}: {h}")
        parts.append("Do NOT repeat previous hints. Build on them.")

    if level == 1:
        parts.append("Keep it very short — a tiny nudge, one sentence.")
    elif level == 2:
        parts.append("Point toward the right evidence. Two sentences max.")
    elif level == 3:
        parts.append("Give nearly complete guidance. Still don't reveal the exact answer.")

    parts.append("NEVER reveal passwords, flags, exact solutions, or hidden answers.")
    return "\n".join(parts)
