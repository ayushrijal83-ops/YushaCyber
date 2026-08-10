"""Roadmap integrity audit (YC-036.2).

Read-only: every function here only queries the database and touches the
filesystem to check whether a lesson's content file exists — nothing is
written, seeded, or migrated. Exposed via ``flask roadmap-audit`` (see
``app/__init__.py``) and reused directly by
``tests/test_roadmap_lock.py`` so the same logic backs both the CLI
report and the CI-enforced invariants.

See docs/ROADMAP_LOCK.md for what "locked" means and why this module
exists.
"""

from __future__ import annotations

from typing import Any

from app.roadmap.content_render import _resolve_safe
from app.roadmap.models import Lesson, RoadmapCategory, RoadmapModule

# A resolved content file smaller than this is almost certainly not real
# lesson content (a stub, a leftover test fixture, or a one-liner) even
# though the file technically exists — calibrated against the two content
# files that exist today: the real one is 925 bytes, the other is a
# 63-byte leftover XSS-sanitisation test payload. See docs/ROADMAP_LOCK.md
# Known Issues #3.
_PLACEHOLDER_BYTE_THRESHOLD = 200

# Every module's lessons currently follow this exact fixed shape (see
# docs/ROADMAP_LOCK.md, "Lesson Order"). Used only to flag lessons whose
# *title* still matches the template placeholder shape, independent of
# whether their content file exists — a lesson can be "empty" (no file),
# "placeholder" (a stub/test-fixture file), or both.
_TEMPLATE_LESSON_TITLES = {"Introduction", "Core Concepts", "Hands-on Practice"}


def _lesson_content_state(lesson: Lesson) -> tuple[bool, bool]:
    """Return ``(is_empty, is_placeholder)`` for one lesson's content file.

    ``is_empty`` — the content file doesn't exist at all (or the path is
    missing/unsafe); the viewer shows "This lesson is coming soon."
    ``is_placeholder`` — a file exists but is too small to plausibly be
    real educational content (see ``_PLACEHOLDER_BYTE_THRESHOLD``). A
    lesson is never both at once.
    """
    path = _resolve_safe(lesson.content_path or "")
    if path is None or not path.is_file():
        return True, False
    try:
        size = path.stat().st_size
    except OSError:
        return True, False
    return False, size < _PLACEHOLDER_BYTE_THRESHOLD


def audit_roadmap() -> dict[str, Any]:
    """Run the full roadmap integrity audit and return a structured report.

    Every top-level key matches the driving spec's requested report
    fields (YC-036.2 §21) exactly. List-valued fields hold enough detail
    (slugs/ids) to act on; scalar counts are always ``len()`` of the
    corresponding list where one exists.
    """
    all_categories = RoadmapCategory.query.order_by(RoadmapCategory.display_order).all()
    all_modules = RoadmapModule.query.order_by(
        RoadmapModule.category_id, RoadmapModule.display_order
    ).all()
    all_lessons = Lesson.query.order_by(
        Lesson.module_id, Lesson.display_order
    ).all()

    category_ids = {c.id for c in all_categories}
    module_ids = {m.id for m in all_modules}

    # ---- published / empty / placeholder ---------------------------------
    # There is no is_published column (see docs/ROADMAP_LOCK.md) — a
    # lesson is reachable ("published") iff its parent module and that
    # module's category are both active.
    active_module_ids = {m.id for m in all_modules if m.is_active}
    published_lessons: list[str] = []
    empty_lessons: list[str] = []
    placeholder_lessons: list[str] = []
    for lesson in all_lessons:
        tag = f"{lesson.module_id}:{lesson.slug}"
        if lesson.module_id in active_module_ids:
            published_lessons.append(tag)
        is_empty, is_placeholder = _lesson_content_state(lesson)
        if is_empty:
            empty_lessons.append(tag)
        elif is_placeholder:
            placeholder_lessons.append(tag)

    # ---- broken links ------------------------------------------------------
    # Neither Lesson nor RoadmapModule carries a lab/mission FK today (an
    # intentional gap — see docs/ROADMAP_LOCK.md's Lab/Mission Mapping),
    # so there is structurally nothing that could be "broken" yet. Kept as
    # real checks (not hardcoded empty) so this function is correct the
    # moment such a column is added.
    broken_prerequisites: list[str] = []
    if hasattr(RoadmapModule, "prerequisite_module_id"):
        for m in all_modules:
            prereq_id = getattr(m, "prerequisite_module_id", None)
            if prereq_id is not None and prereq_id not in module_ids:
                broken_prerequisites.append(m.slug)
    broken_lab_links: list[str] = []
    if hasattr(Lesson, "lab_slug"):
        from app.labs.models import Lab
        real_lab_slugs = {s for (s,) in Lab.query.with_entities(Lab.slug).all()}
        for lesson in all_lessons:
            lab_slug = getattr(lesson, "lab_slug", None)
            if lab_slug and lab_slug not in real_lab_slugs:
                broken_lab_links.append(f"{lesson.module_id}:{lesson.slug}")
    broken_mission_links: list[str] = []
    if hasattr(Lesson, "mission_slug"):
        from app.core.missions.mission_loader import MISSIONS
        for lesson in all_lessons:
            mission_slug = getattr(lesson, "mission_slug", None)
            if mission_slug and mission_slug not in MISSIONS:
                broken_mission_links.append(f"{lesson.module_id}:{lesson.slug}")

    # ---- duplicates ----------------------------------------------------
    seen_module_slugs: dict[str, int] = {}
    duplicate_module_slugs: list[str] = []
    for m in all_modules:
        seen_module_slugs[m.slug] = seen_module_slugs.get(m.slug, 0) + 1
    duplicate_module_slugs = [s for s, n in seen_module_slugs.items() if n > 1]

    seen_lesson_slugs: dict[tuple[int, str], int] = {}
    for lesson in all_lessons:
        key = (lesson.module_id, lesson.slug)
        seen_lesson_slugs[key] = seen_lesson_slugs.get(key, 0) + 1
    duplicate_lesson_slugs = [
        f"{mid}:{slug}" for (mid, slug), n in seen_lesson_slugs.items() if n > 1
    ]

    seen_module_order: dict[tuple[int, int], int] = {}
    for m in all_modules:
        key = (m.category_id, m.display_order)
        seen_module_order[key] = seen_module_order.get(key, 0) + 1
    duplicate_module_ordering = [
        f"category {cid} order {order}"
        for (cid, order), n in seen_module_order.items() if n > 1
    ]

    seen_lesson_order: dict[tuple[int, int], int] = {}
    for lesson in all_lessons:
        key = (lesson.module_id, lesson.display_order)
        seen_lesson_order[key] = seen_lesson_order.get(key, 0) + 1
    duplicate_lesson_ordering = [
        f"module {mid} order {order}"
        for (mid, order), n in seen_lesson_order.items() if n > 1
    ]

    # ---- orphans ---------------------------------------------------------
    orphaned_modules = [m.slug for m in all_modules if m.category_id not in category_ids]
    orphaned_lessons = [
        f"{lesson.module_id}:{lesson.slug}"
        for lesson in all_lessons if lesson.module_id not in module_ids
    ]
    empty_categories = [
        c.title for c in all_categories if not any(m.category_id == c.id for m in all_modules)
    ]

    return {
        "tracks": len(all_categories),
        "modules": len(all_modules),
        "lessons": len(all_lessons),
        "published_lessons": len(published_lessons),
        "empty_lessons": len(empty_lessons),
        "empty_lesson_list": empty_lessons,
        "placeholder_lessons": len(placeholder_lessons),
        "placeholder_lesson_list": placeholder_lessons,
        "broken_prerequisites": broken_prerequisites,
        "broken_lab_links": broken_lab_links,
        "broken_mission_links": broken_mission_links,
        "duplicate_module_slugs": duplicate_module_slugs,
        "duplicate_lesson_slugs": duplicate_lesson_slugs,
        "duplicate_module_ordering": duplicate_module_ordering,
        "duplicate_lesson_ordering": duplicate_lesson_ordering,
        "orphaned_modules": orphaned_modules,
        "orphaned_lessons": orphaned_lessons,
        "empty_categories": empty_categories,
    }


def format_audit_report(report: dict[str, Any]) -> str:
    """Render an ``audit_roadmap()`` result as the plain-text CLI report."""
    lines = [
        f"Tracks:              {report['tracks']}",
        f"Modules:             {report['modules']}",
        f"Lessons:             {report['lessons']}",
        f"Published lessons:   {report['published_lessons']}",
        f"Empty lessons:       {report['empty_lessons']}",
        f"Placeholder lessons: {report['placeholder_lessons']}",
        f"Broken prerequisites: {len(report['broken_prerequisites'])}",
        f"Broken lab links:     {len(report['broken_lab_links'])}",
        f"Broken mission links: {len(report['broken_mission_links'])}",
        f"Duplicate module slugs:     {len(report['duplicate_module_slugs'])}",
        f"Duplicate lesson slugs:     {len(report['duplicate_lesson_slugs'])}",
        f"Duplicate module ordering:  {len(report['duplicate_module_ordering'])}",
        f"Duplicate lesson ordering:  {len(report['duplicate_lesson_ordering'])}",
        f"Orphaned modules:    {len(report['orphaned_modules'])}",
        f"Orphaned lessons:    {len(report['orphaned_lessons'])}",
        f"Empty categories:    {len(report['empty_categories'])}"
        + (f" ({', '.join(report['empty_categories'])})" if report["empty_categories"] else ""),
    ]
    return "\n".join(lines)
