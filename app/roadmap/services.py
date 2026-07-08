"""Roadmap data assembly.

Mirrors the dashboard services pattern: this module is the single place
the roadmap page gets its data from. The tier list below is deliberately
static placeholder content (YC-006.1 is architecture only) — when the
roadmap content system lands in YC-006.2+, these functions swap to real
queries and the routes/templates stay untouched.
"""

from __future__ import annotations

import os
import re
from typing import Any, Optional

import markdown

from app.auth.models import User
from app.dashboard.services import get_nav_items
from app.roadmap.models import Lesson, RoadmapCategory, RoadmapModule


# ---------------------------------------------------------------------------
# Content queries — the ONLY sanctioned way for routes to reach roadmap data.
#
# Query rules (per YC-006.3): filter is_active=True wherever the column
# exists (categories, modules; lessons instead require an active parent
# module), order by display_order, and return None for missing single rows.
# ---------------------------------------------------------------------------
def get_all_categories() -> list[RoadmapCategory]:
    """All active categories in curriculum order."""
    return (
        RoadmapCategory.query
        .filter_by(is_active=True)
        .order_by(RoadmapCategory.display_order)
        .all()
    )


def get_category(category_id: int) -> Optional[RoadmapCategory]:
    """One active category by id, or None."""
    return (
        RoadmapCategory.query
        .filter_by(id=category_id, is_active=True)
        .first()
    )


def get_modules(category_id: int) -> list[RoadmapModule]:
    """Active modules of a category in curriculum order."""
    return (
        RoadmapModule.query
        .filter_by(category_id=category_id, is_active=True)
        .order_by(RoadmapModule.display_order)
        .all()
    )


def get_module(module_slug: str) -> Optional[RoadmapModule]:
    """One active module by its globally-unique slug, or None."""
    return (
        RoadmapModule.query
        .filter_by(slug=module_slug, is_active=True)
        .first()
    )


def get_lessons(module_id: int) -> list[Lesson]:
    """Lessons of an active module in curriculum order.

    Lessons carry no is_active flag (YC-006.2 schema); activity is
    governed by their parent module, which this query enforces via join.
    """
    return (
        Lesson.query
        .join(RoadmapModule, Lesson.module_id == RoadmapModule.id)
        .filter(RoadmapModule.id == module_id, RoadmapModule.is_active.is_(True))
        .order_by(Lesson.display_order)
        .all()
    )


def get_lesson(module_slug: str, lesson_slug: str) -> Optional[Lesson]:
    """One lesson addressed by (module slug, lesson slug), or None.

    Both parts are required because lesson slugs are only unique within
    their module. The parent module must be active.
    """
    return (
        Lesson.query
        .join(RoadmapModule, Lesson.module_id == RoadmapModule.id)
        .filter(
            RoadmapModule.slug == module_slug,
            RoadmapModule.is_active.is_(True),
            Lesson.slug == lesson_slug,
        )
        .first()
    )


def get_dashboard_roadmap() -> list[dict[str, Any]]:
    """Compact roadmap summary for dashboard widgets.

    One entry per active category with its active modules (already in
    curriculum order via the model relationships) reduced to the fields
    a summary card needs — no ORM objects leak past the service layer.
    """
    summary: list[dict[str, Any]] = []
    for category in get_all_categories():
        active_modules = [m for m in category.modules if m.is_active]
        summary.append({
            "id": category.id,
            "title": category.title,
            "description": category.description,
            "icon": category.icon,
            "color": category.color,
            "module_count": len(active_modules),
            "lesson_count": sum(len(m.lessons) for m in active_modules),
            "total_xp": sum(m.xp_reward for m in active_modules),
        })
    return summary


# ---------------------------------------------------------------------------
# Progress placeholders — real implementations arrive with the progress
# system (later YC-006.x). Signatures are final so callers written now
# will not need to change; only the bodies will.
# ---------------------------------------------------------------------------
def get_category_progress(user: User) -> dict[int, int]:
    """PLACEHOLDER: percent complete per category for this user.

    Returns {category_id: percent}; all zeros until UserLessonProgress
    is consulted by the real implementation.
    """
    return {category.id: 0 for category in get_all_categories()}


def get_module_progress(user: User, module: RoadmapModule) -> dict[str, int]:
    """PLACEHOLDER: this user's progress within one module.

    Real lesson totals, zero completion — the shape the UI will bind to.
    """
    total = len(module.lessons) if module is not None else 0
    return {"completed_lessons": 0, "total_lessons": total, "percent": 0}


def lesson_completed(user: User, lesson: Lesson) -> bool:
    """PLACEHOLDER: whether this user completed this lesson.

    Always False until the progress system queries UserLessonProgress.
    """
    return False


def get_lesson_view_context(
    user: User, module_slug: str, lesson_slug: str
) -> Optional[dict[str, Any]]:
    """Assemble the lesson viewer context, or None if not found.

    Built from get_module / get_lesson / get_lessons (for prev-next
    ordering) so no SQLAlchemy query lives in the route. Loads and safely
    renders the lesson's markdown; a missing file yields a friendly
    "coming soon" flag rather than an error. Returns None when the module
    or lesson is missing/inactive, letting the route raise a clean 404.
    """
    module = get_module(module_slug)
    if module is None:
        return None

    lesson = get_lesson(module_slug, lesson_slug)
    if lesson is None:
        return None

    # Prev/next by display_order among the module's active lessons.
    siblings = get_lessons(module.id)
    index = next((i for i, s in enumerate(siblings) if s.id == lesson.id), None)
    prev_slug = siblings[index - 1].slug if index and index > 0 else None
    next_slug = (
        siblings[index + 1].slug
        if index is not None and index + 1 < len(siblings)
        else None
    )

    content_html, content_missing = render_lesson_markdown(lesson.content_path)

    return {
        "module": {"title": module.title, "slug": module.slug},
        "lesson": {
            "title": lesson.title,
            "slug": lesson.slug,
            "lesson_type": lesson.lesson_type,
            "estimated_minutes": lesson.estimated_minutes,
            "xp_reward": lesson.xp_reward,
        },
        "content_html": content_html,
        "content_missing": content_missing,
        "prev_slug": prev_slug,
        "next_slug": next_slug,
        "nav_items": get_nav_items(active="roadmap"),
    }


def render_lesson_markdown(content_path: Optional[str]) -> tuple[str, bool]:
    """Load and safely render a lesson's markdown file.

    Returns ``(html, missing)``. When the file is absent or unreadable,
    ``missing`` is True and the html is a friendly placeholder — the
    viewer never crashes on missing content. Content files live under the
    app's ``content`` directory; paths are resolved safely so a stored
    path cannot escape it.
    """
    placeholder = "<p class=\"lesson-content__soon\">This lesson is coming soon.</p>"
    if not content_path:
        return placeholder, True

    from flask import current_app

    content_root = os.path.join(current_app.root_path, "content")
    # Resolve and confine to the content root (defence against traversal).
    target = os.path.normpath(os.path.join(content_root, content_path))
    if os.path.commonpath([content_root, target]) != content_root:
        return placeholder, True
    if not os.path.isfile(target):
        return placeholder, True

    try:
        with open(target, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return placeholder, True

    html = markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )
    # Sanitise: the content is author-supplied markdown, but we strip any
    # raw <script>/<iframe>/event-handler HTML that slipped through so the
    # viewer renders safely.
    html = _sanitise_lesson_html(html)
    return html, False


def _sanitise_lesson_html(html: str) -> str:
    """Remove script/iframe/style blocks and inline event handlers."""
    html = re.sub(r"(?is)<(script|iframe|style)\b.*?</\1>", "", html)
    html = re.sub(r"(?is)<(script|iframe|style)\b[^>]*>", "", html)
    html = re.sub(r"(?i)\son\w+\s*=\s*\"[^\"]*\"", "", html)
    html = re.sub(r"(?i)\son\w+\s*=\s*'[^']*'", "", html)
    html = re.sub(r"(?i)javascript:", "", html)
    return html


def get_lesson_view_context(
    user: User, module_slug: str, lesson_slug: str
) -> Optional[dict[str, Any]]:
    """Assemble the lesson viewer context, or None if module/lesson missing.

    Built from get_module / get_lesson / get_lessons plus the content
    renderer — no SQLAlchemy in the route or template. Previous/next
    navigation is derived from the module's lessons in display_order.
    ``content_html`` is None when the markdown file doesn't exist yet,
    letting the view show a "coming soon" message.
    """
    from app.roadmap.content_render import render_lesson_content

    module = get_module(module_slug)
    if module is None:
        return None

    lesson = get_lesson(module_slug, lesson_slug)
    if lesson is None:
        return None

    # Ordered lessons of this module → locate previous / next neighbours.
    ordered = get_lessons(module.id)
    index = next((i for i, l in enumerate(ordered) if l.id == lesson.id), None)

    prev_slug = ordered[index - 1].slug if index not in (None, 0) else None
    next_slug = (
        ordered[index + 1].slug
        if index is not None and index + 1 < len(ordered)
        else None
    )

    return {
        "module": {"title": module.title, "slug": module.slug},
        "lesson": {
            "title": lesson.title,
            "slug": lesson.slug,
            "lesson_type": lesson.lesson_type,
            "estimated_minutes": lesson.estimated_minutes,
            "xp_reward": lesson.xp_reward,
            "completed": lesson_completed(user, lesson),
        },
        "content_html": render_lesson_content(lesson.content_path),
        "prev_slug": prev_slug,
        "next_slug": next_slug,
        "nav_items": get_nav_items(active="roadmap"),
    }


def get_module_detail_context(user: User, module_slug: str) -> Optional[dict[str, Any]]:
    """Assemble the module detail page context, or None if not found.

    Built from the YC-006.3 service functions (get_module / get_lessons)
    plus the progress placeholders, so no SQLAlchemy query lives in the
    route or template. Returns None when the module is missing/inactive,
    letting the route raise a clean 404.
    """
    module = get_module(module_slug)
    if module is None:
        return None

    lessons = get_lessons(module.id)
    lesson_views = [
        {
            "title": lesson.title,
            "slug": lesson.slug,
            "lesson_type": lesson.lesson_type,
            "estimated_minutes": lesson.estimated_minutes,
            "xp_reward": lesson.xp_reward,
            "is_preview": lesson.is_preview,
            # Progress system not implemented — placeholder status.
            "completed": lesson_completed(user, lesson),
        }
        for lesson in lessons
    ]

    return {
        "module": {
            "title": module.title,
            "slug": module.slug,
            "description": module.description,
            "difficulty": module.difficulty,
            "estimated_hours": module.estimated_hours,
            "xp_reward": module.xp_reward,
            "is_locked": module.is_locked,
        },
        "lessons": lesson_views,
        "nav_items": get_nav_items(active="roadmap"),
    }


def get_roadmap_context(user: User) -> dict[str, Any]:
    """Assemble the full roadmap tree: categories → modules → lessons.

    Built entirely from the YC-006.3 service functions so no SQLAlchemy
    query lives in the route or template. The category/module
    relationships use selectin loading (declared on the models), so the
    whole tree loads without N+1 queries. Progress values come from the
    placeholder helpers and read 0% until completion logic exists.
    """
    categories: list[dict[str, Any]] = []

    for category in get_all_categories():
        modules = get_modules(category.id)
        category_lessons = 0
        module_views: list[dict[str, Any]] = []

        for module in modules:
            lessons = get_lessons(module.id)
            category_lessons += len(lessons)
            mod_progress = get_module_progress(user, module)

            module_views.append({
                "title": module.title,
                "slug": module.slug,
                "difficulty": module.difficulty,
                "estimated_hours": module.estimated_hours,
                "xp_reward": module.xp_reward,
                "is_locked": module.is_locked,
                "lesson_count": len(lessons),
                "progress_percent": mod_progress["percent"],
                "lessons": [
                    {
                        "title": lesson.title,
                        "slug": lesson.slug,
                        "module_slug": module.slug,
                        "lesson_type": lesson.lesson_type,
                        "xp_reward": lesson.xp_reward,
                        "estimated_minutes": lesson.estimated_minutes,
                        "is_preview": lesson.is_preview,
                        "completed": lesson_completed(user, lesson),
                    }
                    for lesson in lessons
                ],
            })

        cat_progress = get_category_progress(user).get(category.id, 0)
        categories.append({
            "id": category.id,
            "title": category.title,
            "description": category.description,
            "icon": category.icon,
            "color": category.color,
            "module_count": len(modules),
            "lesson_count": category_lessons,
            "total_xp": sum(m.xp_reward for m in modules),
            "progress_percent": cat_progress,
            "modules": module_views,
        })

    return {
        "categories": categories,
        "nav_items": get_nav_items(active="roadmap"),
    }


def _get_tiers() -> list[dict[str, str]]:
    """Retained for reference / fallback; no longer used by the page."""
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
