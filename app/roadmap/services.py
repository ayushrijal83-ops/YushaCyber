"""Roadmap data assembly.

Mirrors the dashboard services pattern: this module is the single place
the roadmap page gets its data from. The tier list below is deliberately
static placeholder content (YC-006.1 is architecture only) — when the
roadmap content system lands in YC-006.2+, these functions swap to real
queries and the routes/templates stay untouched.
"""

from __future__ import annotations

from typing import Any

from app.auth.models import User
from app.dashboard.services import get_nav_items


def get_roadmap_context(user: User) -> dict[str, Any]:
    """Assemble everything the roadmap template needs."""
    return {
        "tiers": _get_tiers(),
        "nav_items": get_nav_items(active="roadmap"),
    }


def _get_tiers() -> list[dict[str, str]]:
    """The four learning tiers. PLACEHOLDER — no database, per ticket."""
    return [
        {"key": "beginner", "title": "Beginner", "icon": "terminal", "color": "green",
         "blurb": "Terminal basics, networking fundamentals and your first labs."},
        {"key": "intermediate", "title": "Intermediate", "icon": "map", "color": "blue",
         "blurb": "Scanning, scripting and the tools of the trade."},
        {"key": "advanced", "title": "Advanced", "icon": "zap", "color": "orange",
         "blurb": "Web exploitation, OWASP Top 10 and chained attacks."},
        {"key": "ai-security", "title": "AI Security", "icon": "flag", "color": "purple",
         "blurb": "Prompt injection, model attacks and securing AI systems."},
    ]
