"""Dashboard data assembly.

This module is the single place the dashboard gets its data from. Today
most values are placeholders (per YC dashboard ticket: UI only); when the
XP, courses, achievements and activity features land, each function here
swaps its static payload for a real query — the routes and templates
stay untouched.

Real user fields (level, xp, streak, role) are already read from the
User model rather than hardcoded, so the dashboard reflects genuine
account data from day one.
"""

from __future__ import annotations

from typing import Any

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from app.extensions import db

# ---------------------------------------------------------------------------
# XP / Level engine
#
# Single source of truth for progression. Every future feature (lessons,
# quizzes, courses, daily challenges, CTF, achievements, admin panel,
# AI mentor) awards XP exclusively through award_xp() — never by writing
# user.xp directly — so level recalculation can never be forgotten.
#
# Level thresholds (cumulative XP required to REACH a level):
#   L1: 0 · L2: 100 · L3: 250 · L4: 450 · L5: 700
#   L6+: previous threshold + 300 per level (L6=1000, L7=1300, …)
# ---------------------------------------------------------------------------
_BASE_THRESHOLDS: tuple[int, ...] = (0, 100, 250, 450, 700)  # levels 1–5
_XP_PER_LEVEL_AFTER_5 = 300


def xp_threshold_for_level(level: int) -> int:
    """Cumulative XP required to reach ``level``."""
    if level <= 1:
        return 0
    if level <= len(_BASE_THRESHOLDS):
        return _BASE_THRESHOLDS[level - 1]
    return _BASE_THRESHOLDS[-1] + _XP_PER_LEVEL_AFTER_5 * (level - len(_BASE_THRESHOLDS))


def calculate_level(xp: int) -> int:
    """Level corresponding to a total XP amount."""
    xp = max(0, xp)
    level = 1
    while xp >= xp_threshold_for_level(level + 1):
        level += 1
    return level


def xp_needed_for_next_level(level: int) -> int:
    """Cumulative XP threshold of the NEXT level (the target to display)."""
    return xp_threshold_for_level(max(1, level) + 1)


def progress_percentage(xp: int) -> int:
    """Percent progress through the current level (0–100)."""
    xp = max(0, xp)
    level = calculate_level(xp)
    current = xp_threshold_for_level(level)
    nxt = xp_threshold_for_level(level + 1)
    span = nxt - current
    if span <= 0:  # defensive; thresholds are strictly increasing
        return 100
    # Floor, not round: the bar must only read 100% at an actual level-up.
    return max(0, min(100, int((xp - current) / span * 100)))


def award_xp(user: User, amount: int) -> User:
    """Award XP to a user, recalculate their level, and persist.

    Returns the updated user. Negative or zero amounts are ignored
    (XP is only ever earned; penalties are not part of the design).
    Rolls back and logs on database failure, leaving the user unchanged.
    """
    if amount <= 0:
        return user

    previous_level = user.level
    user.xp = max(0, (user.xp or 0)) + amount
    user.level = calculate_level(user.xp)

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to award %s XP to user %s", amount, user.id)
        return user

    if user.level > previous_level:
        current_app.logger.info(
            "User %s leveled up: %s -> %s (xp=%s)",
            user.id, previous_level, user.level, user.xp,
        )
    return user


def get_xp_info(user: User) -> dict[str, int]:
    """Everything the UI needs to render XP state, computed from the DB."""
    xp = max(0, user.xp or 0)
    level = calculate_level(xp)
    current_threshold = xp_threshold_for_level(level)
    next_threshold = xp_needed_for_next_level(level)
    return {
        "xp": xp,
        "level": level,
        "current_threshold": current_threshold,
        "next_threshold": next_threshold,
        "xp_into_level": xp - current_threshold,
        "xp_span": next_threshold - current_threshold,
        "percent": progress_percentage(xp),
    }


def get_dashboard_context(user: User) -> dict[str, Any]:
    """Assemble everything the dashboard template needs."""
    from app.roadmap.quiz_services import get_dashboard_quiz_context

    return {
        "xp_info": get_xp_info(user),
        "stats": _get_stats(user),
        "quick_actions": _get_quick_actions(),
        "recent_activity": _get_recent_activity(user),
        "learning_progress": _get_learning_progress(user),
        "achievements": _get_achievements(user),
        "quiz_analytics": get_dashboard_quiz_context(user),
        "nav_items": get_nav_items(active="dashboard"),
    }


def get_nav_items(active: str) -> list[dict[str, str | bool]]:
    """Sidebar navigation. Future feature pages plug in real endpoints."""
    items = [
        {"key": "dashboard", "label": "Dashboard", "icon": "grid", "url": "/dashboard/"},
        {"key": "roadmap", "label": "Roadmap", "icon": "map", "url": "/roadmap/"},
        {"key": "courses", "label": "Courses", "icon": "book", "url": "/#courses"},
        {"key": "lessons", "label": "Lessons", "icon": "layers", "url": "#"},
        {"key": "quizzes", "label": "Quizzes", "icon": "help", "url": "/roadmap/quizzes/"},
        {"key": "challenge", "label": "Daily Challenge", "icon": "zap", "url": "/#challenge"},
        {"key": "ctf", "label": "CTF Arena", "icon": "flag", "url": "/#ctf"},
        {"key": "achievements", "label": "Achievements", "icon": "award", "url": "/dashboard/achievements"},
        {"key": "certificates", "label": "Certificates", "icon": "file-text", "url": "/dashboard/certificates"},
        {"key": "settings", "label": "Settings", "icon": "settings", "url": "#"},
    ]
    for item in items:
        item["active"] = item["key"] == active
    return items


# ---------------------------------------------------------------------------
# Section data — placeholder-backed, database-shaped.
# ---------------------------------------------------------------------------
def _get_stats(user: User) -> list[dict[str, Any]]:
    """The four stat cards. Level/XP/streak come from the real account."""
    return [
        {"key": "level", "label": "Level", "value": user.level, "icon": "trending",
         "hint": "Earn XP to level up"},
        {"key": "xp", "label": "XP", "value": user.xp, "icon": "zap",
         "hint": "Total experience points"},
        {"key": "streak", "label": "Streak", "value": user.streak, "icon": "flame",
         "hint": "Consecutive active days"},
        # Placeholder until the courses feature lands (course progress table).
        {"key": "courses", "label": "Courses Completed", "value": 0, "icon": "book",
         "hint": "Finished courses"},
    ]


def _get_quick_actions() -> list[dict[str, str]]:
    """Large action buttons. Targets move to real pages as features ship."""
    return [
        {"label": "Continue Learning", "icon": "play", "url": "/#courses",
         "style": "primary"},
        {"label": "Explore Roadmap", "icon": "map", "url": "/#roadmap",
         "style": "outline"},
        {"label": "Solve Daily Challenge", "icon": "zap", "url": "/#challenge",
         "style": "outline"},
        {"label": "Go to CTF Arena", "icon": "flag", "url": "/#ctf",
         "style": "outline"},
    ]


def _get_recent_activity(user: User) -> list[dict[str, str]]:
    """Timeline entries. PLACEHOLDER — future activity/events table."""
    joined = user.created_at.strftime("%b %d, %Y") if user.created_at else "today"
    return [
        {"icon": "user", "title": "Account created",
         "detail": f"Welcome aboard — joined {joined}.", "time": "Start"},
        {"icon": "map", "title": "Roadmap unlocked",
         "detail": "8 stages from Linux to CTF are ready for you.", "time": "Next"},
        {"icon": "play", "title": "First lesson awaits",
         "detail": "Linux Essentials · Lesson 01: The Terminal.", "time": "Todo"},
        {"icon": "zap", "title": "Daily challenge available",
         "detail": "Solve today's challenge to start your streak.", "time": "Todo"},
    ]


def _get_learning_progress(user: User) -> list[dict[str, Any]]:
    """Progress bars. PLACEHOLDER percentages — future progress table."""
    return [
        {"label": "Networking", "percent": 0},
        {"label": "Linux", "percent": 0},
        {"label": "Python", "percent": 0},
        {"label": "Web Security", "percent": 0},
    ]


def _get_achievements(user: User) -> list[dict[str, Any]]:
    """Six badge previews. PLACEHOLDER — future achievements table."""
    return [
        {"icon": "terminal", "title": "First Steps", "unlocked": True,
         "detail": "Created your account"},
        {"icon": "flame", "title": "On Fire", "unlocked": False,
         "detail": "7-day streak"},
        {"icon": "book", "title": "Bookworm", "unlocked": False,
         "detail": "Complete a course"},
        {"icon": "flag", "title": "Flag Bearer", "unlocked": False,
         "detail": "Capture your first flag"},
        {"icon": "zap", "title": "Challenger", "unlocked": False,
         "detail": "Solve 10 daily challenges"},
        {"icon": "award", "title": "Century", "unlocked": False,
         "detail": "Earn 100 XP"},
    ]
