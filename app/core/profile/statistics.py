"""Profile statistics — reusable stat helpers.

Thin wrapper over the analytics engine for profile-specific stats.
"""

from __future__ import annotations

from typing import Any

from app.core.profile.types import ProfileStatistics


def stats_to_display(stats: ProfileStatistics) -> list[dict[str, Any]]:
    """Convert stats to a list of display-ready dicts."""
    return [
        {"label": "Total XP", "value": f"{stats.total_xp:,}",
         "icon": "⚡"},
        {"label": "Level", "value": str(stats.level), "icon": "📊"},
        {"label": "Labs Completed", "value": str(stats.completed_labs),
         "icon": "🧪"},
        {"label": "Certificates", "value": str(stats.certificates_earned),
         "icon": "📜"},
        {"label": "Achievements", "value": str(stats.achievements_earned),
         "icon": "🏆"},
        {"label": "Leaderboard", "value": f"#{stats.leaderboard_rank}",
         "icon": "🏅"},
    ]
