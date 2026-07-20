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
        "continue_learning": _get_continue_learning(user),
        "active_roadmap": _get_active_roadmap(user),
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
        {"key": "ctf", "label": "CTF Arena", "icon": "flag", "url": "/ctf/"},
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
    """The four stat cards — all real account data (YC-022.0)."""
    from app.roadmap.models import UserModuleProgress

    modules_done = UserModuleProgress.query.filter_by(
        user_id=user.id, completed=True).count()
    return [
        {"key": "level", "label": "Level", "value": user.level, "icon": "trending",
         "hint": "Earn XP to level up"},
        {"key": "xp", "label": "XP", "value": user.xp, "icon": "zap",
         "hint": "Total experience points"},
        {"key": "streak", "label": "Streak", "value": user.streak, "icon": "flame",
         "hint": "Consecutive active days"},
        {"key": "modules", "label": "Modules Completed", "value": modules_done,
         "icon": "book", "hint": "Finished roadmap modules"},
    ]


def _get_quick_actions() -> list[dict[str, str]]:
    """Quick Access cards — every target is a real page (YC-022.0)."""
    return [
        {"label": "Continue Learning", "icon": "play", "url": "/roadmap/",
         "style": "primary"},
        {"label": "Open Labs", "icon": "cpu", "url": "/labs/",
         "style": "outline"},
        {"label": "CTF Arena", "icon": "flag", "url": "/ctf/",
         "style": "outline"},
        {"label": "Browse Resources", "icon": "book", "url": "/resources/",
         "style": "outline"},
    ]


def _get_recent_activity(user: User) -> list[dict[str, Any]]:
    """Real activity feed (YC-022.0): latest achievement unlocks, lab
    completions and CTF solves, merged newest-first. Three small indexed
    queries; falls back to a friendly onboarding timeline for new users."""
    from app.achievement.models import Achievement, UserAchievement
    from app.ctf.models import Challenge, ChallengeSolve
    from app.labs.models import Lab, UserLabProgress

    events: list[tuple] = []

    unlocks = (
        db.session.query(UserAchievement.unlocked_at, Achievement.title)
        .join(Achievement, Achievement.id == UserAchievement.achievement_id)
        .filter(UserAchievement.user_id == user.id,
                UserAchievement.unlocked_at.isnot(None))
        .order_by(UserAchievement.unlocked_at.desc())
        .limit(4).all()
    )
    events += [(ts, "target", f"Achievement unlocked — {title}", "Achievements")
               for ts, title in unlocks]

    labs_done = (
        db.session.query(UserLabProgress.completed_at, Lab.title)
        .join(Lab, Lab.id == UserLabProgress.lab_id)
        .filter(UserLabProgress.user_id == user.id,
                UserLabProgress.completed.is_(True),
                UserLabProgress.completed_at.isnot(None))
        .order_by(UserLabProgress.completed_at.desc())
        .limit(4).all()
    )
    events += [(ts, "cpu", f"Completed lab — {title}", "Labs")
               for ts, title in labs_done]

    solves = (
        db.session.query(ChallengeSolve.solved_at, Challenge.title)
        .join(Challenge, Challenge.id == ChallengeSolve.challenge_id)
        .filter(ChallengeSolve.user_id == user.id,
                ChallengeSolve.solved.is_(True),
                ChallengeSolve.solved_at.isnot(None))
        .order_by(ChallengeSolve.solved_at.desc())
        .limit(4).all()
    )
    events += [(ts, "flag", f"Captured flag — {title}", "CTF")
               for ts, title in solves]

    events.sort(key=lambda e: e[0], reverse=True)
    if events:
        return [
            {"icon": icon, "title": title, "detail": area,
             "time": ts.strftime("%b %d")}
            for ts, icon, title, area in events[:6]
        ]

    # New account — show the onboarding path instead of an empty panel.
    joined = user.created_at.strftime("%b %d, %Y") if user.created_at else "today"
    return [
        {"icon": "user", "title": "Account created",
         "detail": f"Welcome aboard — joined {joined}.", "time": "Start"},
        {"icon": "map", "title": "Roadmap unlocked",
         "detail": "Structured paths from Linux to CTF are ready.", "time": "Next"},
        {"icon": "cpu", "title": "First lab awaits",
         "detail": "Open the Labs section and try the terminal.", "time": "Todo"},
    ]


def _get_learning_progress(user: User) -> list[dict[str, Any]]:
    """Real per-category roadmap progress (was a placeholder)."""
    from app.roadmap.services import get_all_categories, get_category_progress

    progress = get_category_progress(user)  # one batched computation
    return [
        {"label": cat.title, "percent": progress.get(cat.id, 0)}
        for cat in get_all_categories()
    ]


def _get_achievements(user: User) -> list[dict[str, Any]]:
    """Recent REAL achievements: newest unlocks first, padded with the next
    locked ones so the panel always previews what to chase (max 6)."""
    from app.achievement.models import Achievement, UserAchievement

    rows = (
        db.session.query(Achievement, UserAchievement.unlocked_at)
        .outerjoin(UserAchievement,
                   (UserAchievement.achievement_id == Achievement.id)
                   & (UserAchievement.user_id == user.id))
        .filter(Achievement.is_active.is_(True))
        .order_by(UserAchievement.unlocked_at.desc().nullslast(),
                  Achievement.display_order)
        .limit(6).all()
    )
    return [
        {"icon": a.icon or "award", "title": a.title,
         "unlocked": ts is not None, "detail": a.description,
         "when": ts.strftime("%b %d") if ts else None}
        for a, ts in rows
    ]


def _get_continue_learning(user: User) -> dict[str, Any] | None:
    """The user's next step in the roadmap: the first available module that
    isn't finished, plus its first incomplete lesson (YC-022.0)."""
    from app.roadmap.services import (
        _completed_lesson_ids, get_all_categories, get_lessons, get_modules,
        get_module_progress, module_status,
    )

    for category in get_all_categories():
        for module in get_modules(category.id):
            if module_status(user, module) != "available":
                continue
            lessons = get_lessons(module.id)
            if not lessons:
                continue
            done = _completed_lesson_ids(user, [l.id for l in lessons])
            next_lesson = next((l for l in lessons if l.id not in done), None)
            progress = get_module_progress(user, module)
            return {
                "category": category.title,
                "module_title": module.title,
                "module_slug": module.slug,
                "lesson_title": next_lesson.title if next_lesson else None,
                "lesson_slug": next_lesson.slug if next_lesson else None,
                "percent": progress["percent"],
                "done": progress.get("completed_lessons", len(done)),
                "total": len(lessons),
            }
    return None


def _get_active_roadmap(user: User) -> dict[str, Any] | None:
    """The category the user is actively working through — highest non-zero
    progress wins; brand-new users get the first category at 0%."""
    from app.roadmap.services import get_all_categories, get_category_progress

    categories = get_all_categories()
    if not categories:
        return None
    progress = get_category_progress(user)

    active = max(categories, key=lambda c: progress.get(c.id, 0))
    if progress.get(active.id, 0) == 0:
        active = categories[0]
    return {
        "title": active.title,
        "icon": active.icon,
        "percent": progress.get(active.id, 0),
        "description": active.description,
    }


# ---------------------------------------------------------------------------
# Profile page (YC-022.0) — read-only summary built from existing tables.
# ---------------------------------------------------------------------------
def get_profile_context(user: User) -> dict[str, Any]:
    """Everything the profile page needs — five cheap indexed COUNT queries,
    no new models, no writes."""
    from app.achievement.models import Achievement, UserAchievement
    from app.certificates.models import UserCertificate
    from app.ctf.models import ChallengeSolve
    from app.labs.models import UserLabProgress
    from app.roadmap.models import UserLessonProgress

    achievements_unlocked = UserAchievement.query.filter_by(user_id=user.id).count()
    achievements_total = Achievement.query.filter_by(is_active=True).count()

    return {
        "xp_info": get_xp_info(user),
        "profile_stats": [
            {"icon": "book", "label": "Lessons Completed",
             "value": UserLessonProgress.query.filter_by(
                 user_id=user.id, completed=True).count()},
            {"icon": "cpu", "label": "Labs Completed",
             "value": UserLabProgress.query.filter_by(
                 user_id=user.id, completed=True).count()},
            {"icon": "flag", "label": "CTF Solves",
             "value": ChallengeSolve.query.filter_by(
                 user_id=user.id, solved=True).count()},
            {"icon": "target", "label": "Achievements",
             "value": f"{achievements_unlocked} / {achievements_total}"},
            {"icon": "award", "label": "Certificates",
             "value": UserCertificate.query.filter_by(user_id=user.id).count()},
        ],
    }
