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
from datetime import datetime, timezone
from typing import Any, Optional

import markdown
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from app.dashboard.services import award_xp, get_nav_items
from app.extensions import db
from app.roadmap.models import (
    Lesson,
    Quiz,
    QuizOption,
    QuizQuestion,
    RoadmapCategory,
    RoadmapModule,
    UserLessonProgress,
    UserModuleProgress,
    UserQuizAttempt,
)

# The locked curriculum's version (YC-036.2 — see docs/ROADMAP_LOCK.md).
# Bump only on a deliberate structural change to the roadmap (track/module/
# lesson hierarchy, ordering, or prerequisites) — never for lesson content
# edits, which are explicitly allowed to improve without a version bump.
ROADMAP_VERSION = "1.0"


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
# Progress — backed by the real UserLessonProgress table (YC-006.9).
# ---------------------------------------------------------------------------
def lesson_completed(user: User, lesson: Lesson) -> bool:
    """True if this user has a completed progress row for this lesson."""
    if user is None or lesson is None:
        return False
    row = UserLessonProgress.query.filter_by(
        user_id=user.id, lesson_id=lesson.id, completed=True
    ).first()
    return row is not None


def _completed_lesson_ids(user: User, lesson_ids: list[int]) -> set[int]:
    """Completed lesson ids for this user within the given set (one query)."""
    if user is None or not lesson_ids:
        return set()
    rows = (
        UserLessonProgress.query
        .filter(
            UserLessonProgress.user_id == user.id,
            UserLessonProgress.completed.is_(True),
            UserLessonProgress.lesson_id.in_(lesson_ids),
        )
        .all()
    )
    return {r.lesson_id for r in rows}


def _percent(done: int, total: int) -> int:
    """Integer percent (floored), 0 when there is nothing to complete."""
    if total <= 0:
        return 0
    return int(done / total * 100)


def get_module_progress(user: User, module: RoadmapModule) -> dict[str, int]:
    """This user's completion within one module (real counts)."""
    total = len(module.lessons) if module is not None else 0
    if total == 0 or user is None:
        return {"completed_lessons": 0, "total_lessons": total, "percent": 0}

    lesson_ids = [l.id for l in module.lessons]
    done = len(_completed_lesson_ids(user, lesson_ids))
    return {
        "completed_lessons": done,
        "total_lessons": total,
        "percent": _percent(done, total),
    }


def get_category_progress(user: User) -> dict[int, int]:
    """Percent complete per category id for this user (real counts)."""
    # YC-022.0 perf: ONE batched completion lookup across every category
    # instead of one query per category.
    per_category: dict[int, list[int]] = {}
    all_ids: list[int] = []
    for category in get_all_categories():
        ids: list[int] = []
        for module in get_modules(category.id):
            ids.extend(l.id for l in module.lessons)
        per_category[category.id] = ids
        all_ids.extend(ids)

    done_all = _completed_lesson_ids(user, all_ids)
    return {
        cat_id: _percent(sum(1 for i in ids if i in done_all), len(ids))
        for cat_id, ids in per_category.items()
    }


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
            "id": lesson.id,
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


# Terminal/mission cross-links for specific lessons (YC-036.4). Keyed by
# (module_slug, lesson_slug); a lesson not listed here simply gets no
# practice block. See docs/ROADMAP_LOCK.md "Mission Mapping" — this is
# the first lesson-to-mission link actually wired into the UI, scoped
# deliberately to the one lesson it was written to reinforce rather than
# guessed for every module.
_LESSON_MISSION_LINKS: dict[tuple[str, str], dict[str, str]] = {
    ("linux-fundamentals", "hands-on-practice"): {
        "mission_slug": "linux-basics",
        "mission_title": "Linux Basics",
    },
    # computer-networking (YC-036.5): the free-practice terminal
    # (`/terminal`, below) never attaches a simulated network to the
    # shell — only the terminal MISSION runner does — so `ping`/`ip`/`ss`/
    # `nslookup` (everything this module teaches) only actually works
    # inside the real mission. Linked from both lessons that teach
    # network commands; core-concepts (addressing/subnetting math, no
    # commands) intentionally gets no practice CTA at all.
    ("computer-networking", "introduction"): {
        "mission_slug": "networking-fundamentals",
        "mission_title": "Networking Fundamentals",
    },
    ("computer-networking", "hands-on-practice"): {
        "mission_slug": "networking-fundamentals",
        "mission_title": "Networking Fundamentals",
    },
    # web-fundamentals (YC-036.6): same reasoning as computer-networking —
    # the free-practice terminal's bare sandbox never attaches a simulated
    # web app (`shell.web_lab` is only ever set by the mission runner, see
    # `app/core/missions/mission_runner.py:_attach_web_lab`), so `open`/
    # `headers`/`cookies`/`response` (everything this module teaches) only
    # work inside a real mission. Unlike computer-networking, all three
    # lessons here use those commands directly (including core-concepts'
    # Challenge exercise), so all three link to the mission.
    ("web-fundamentals", "introduction"): {
        "mission_slug": "web-fundamentals",
        "mission_title": "Web Fundamentals",
    },
    ("web-fundamentals", "core-concepts"): {
        "mission_slug": "web-fundamentals",
        "mission_title": "Web Fundamentals",
    },
    ("web-fundamentals", "hands-on-practice"): {
        "mission_slug": "web-fundamentals",
        "mission_title": "Web Fundamentals",
    },
    # operating-systems (YC-036.9): the real Linux Permissions mission
    # (`whoami`/`id`/`groups`/`ls -l`/`chmod`/`chown` against a realistic
    # filesystem) was already real but unused by any lesson anywhere —
    # a genuine match for this lesson's identity/permissions material
    # (Section 4), not a guessed link. Scoped to hands-on-practice only:
    # introduction also teaches real bare-sandbox commands (`whoami`,
    # `uname`) so it gets the free-practice terminal link below, but
    # core-concepts is entirely conceptual (process/thread/memory theory,
    # no commands at all) and correctly gets neither a mission nor a lab
    # CTA — no practice link where there's nothing to practice, same
    # discipline as computer-networking's core-concepts.
    ("operating-systems", "hands-on-practice"): {
        "mission_slug": "linux-permissions",
        "mission_title": "Linux Permissions",
    },
}

# Modules whose lessons should all offer the free-practice terminal link,
# even lessons with no scored mission attached to them specifically. Only
# for modules whose taught commands work in the bare, network-less
# sandbox (filesystem commands) — see the note above for why
# computer-networking (and, as of YC-036.6, web-fundamentals) are
# deliberately excluded. operating-systems (YC-036.9) joins linux-
# fundamentals here: `whoami`/`id`/`groups`/`uname`/`uname -a` (this
# module's own commands, verified against app/core/terminal/commands.py)
# all work in the bare sandbox with no mission/network attachment needed.
_TERMINAL_PRACTICE_MODULES: set[str] = {"linux-fundamentals", "operating-systems"}

# Lesson -> real interactive lab cross-links (YC-036.6). Deliberately
# scoped and additive, same discipline as _LESSON_MISSION_LINKS: only
# real, existing lab slugs (see docs/ROADMAP_LOCK.md "Labs — audited
# inventory"), picked because their actual content matches what that
# specific lesson teaches — not one generic lab per module. Previous
# tickets (YC-036.4/.5) documented lab-linking as a real gap left for
# whoever picked up the next module; this is that pickup, still scoped
# to the one module it was written for rather than guessed for all 32.
_LESSON_LAB_LINKS: dict[tuple[str, str], dict[str, str]] = {
    ("web-fundamentals", "core-concepts"): {
        "lab_slug": "websec-http",
        "lab_title": "HTTP Requests & Responses",
    },
    ("web-fundamentals", "hands-on-practice"): {
        "lab_slug": "websec-cookies",
        "lab_title": "Cookie Security Flags",
    },
    # operating-systems (YC-036.9): the real Processes lab (`ps`/`top`/
    # `kill`/`jobs` against a simulated runaway process) reinforces this
    # lesson's process-lifecycle material directly — matched by actual
    # content, not a generic per-module guess. Not linked from
    # introduction/core-concepts since neither teaches process commands.
    ("operating-systems", "hands-on-practice"): {
        "lab_slug": "linux-processes",
        "lab_title": "Processes",
    },
    # virtualization (YC-037.0): the real Cloud Basics lab is the only
    # place on this platform where a student can inspect actual virtual
    # machines — `list-vms`/`get-vm` return a VM's state, size, subnet
    # and public IP, and `network` shows the virtual network they sit
    # in, which is precisely this lesson's Section 12 material. Linked
    # for those commands specifically (the lab's IAM/storage/audit
    # objectives go beyond this module into cloud security proper, which
    # the lesson says outright rather than overselling the match).
    # Scoped to hands-on-practice only: introduction and core-concepts
    # are conceptual and teach no commands at all, so neither gets a
    # practice CTA — same discipline as computer-networking's
    # core-concepts. `virtualization` is deliberately NOT added to
    # _TERMINAL_PRACTICE_MODULES: the terminal's @cmd registry has no
    # hypervisor/VM command whatsoever, so a free-practice link would
    # send students somewhere nothing in this module works.
    ("virtualization", "hands-on-practice"): {
        "lab_slug": "cloud-orientation",
        "lab_title": "Cloud Basics: Tour the Account",
    },
}


def _lesson_practice_links(module_slug: str, lesson_slug: str) -> dict[str, Any]:
    """Terminal/mission/lab cross-links for a lesson, or {} if none apply.

    The link kinds are independent: a module's free-practice terminal link
    (``show_terminal``), a lesson's scored-mission link, and a lesson's
    reinforcing-lab link are looked up separately, since a module may have
    real mission reinforcement (computer-networking, web-fundamentals)
    without its taught commands working in the bare, network-less
    free-practice sandbox (see the module-level notes above
    `_LESSON_MISSION_LINKS` / `_TERMINAL_PRACTICE_MODULES`).
    """
    links: dict[str, Any] = {}
    if module_slug in _TERMINAL_PRACTICE_MODULES:
        links["show_terminal"] = True
    mission = _LESSON_MISSION_LINKS.get((module_slug, lesson_slug))
    if mission is not None:
        links["mission_slug"] = mission["mission_slug"]
        links["mission_title"] = mission["mission_title"]
    lab = _LESSON_LAB_LINKS.get((module_slug, lesson_slug))
    if lab is not None:
        links["lab_slug"] = lab["lab_slug"]
        links["lab_title"] = lab["lab_title"]
    return links


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
            "id": lesson.id,
            "title": lesson.title,
            "slug": lesson.slug,
            "lesson_type": lesson.lesson_type,
            "estimated_minutes": lesson.estimated_minutes,
            "xp_reward": lesson.xp_reward,
            "completed": lesson_completed(user, lesson),
            "is_preview": lesson.is_preview,
        },
        "content_html": render_lesson_content(lesson.content_path),
        "prev_slug": prev_slug,
        "next_slug": next_slug,
        # Server-side lock gate (YC-036.2) — the route redirects away
        # rather than rendering real content when this is True, so
        # locked modules can no longer be read/completed via direct URL.
        "locked": lesson_locked_for_user(user, module, lesson),
        "practice": _lesson_practice_links(module.slug, lesson.slug),
        "nav_items": get_nav_items(active="roadmap"),
    }


def _get_or_create_module_progress(user, module) -> "UserModuleProgress":
    """Fetch this user's progress row for a module, creating it if absent.

    New rows default to locked/incomplete. The first module of a category
    is unlocked here so progression works even for modules created after
    the user registered. Caller is responsible for committing.
    """
    row = UserModuleProgress.query.filter_by(
        user_id=user.id, module_id=module.id
    ).first()
    if row is None:
        siblings = get_modules(module.category_id)
        is_first = bool(siblings) and siblings[0].id == module.id
        row = UserModuleProgress(
            user_id=user.id, module_id=module.id,
            unlocked=is_first, completed=False, bonus_awarded=False,
        )
        db.session.add(row)
    return row


def initialize_user_progression(user) -> None:
    """Create module-progress rows for a user, unlocking each category's first.

    Idempotent: modules that already have a row are left untouched, so
    this is safe to call on registration and safe to re-run. Commits once.
    """
    try:
        # YC-022.0 perf fast path: if the user already has a progress row for
        # every active module, there is nothing to create — two COUNT queries
        # instead of one SELECT per module on every roadmap page load.
        total_modules = (
            RoadmapModule.query.filter_by(is_active=True).count()
        )
        existing_rows = UserModuleProgress.query.filter_by(
            user_id=user.id
        ).count()
        if existing_rows >= total_modules:
            return

        # One batched fetch of the rows that DO exist (instead of per-module).
        existing_ids = {
            mid for (mid,) in db.session.query(
                UserModuleProgress.module_id
            ).filter_by(user_id=user.id).all()
        }
        for category in get_all_categories():
            modules = get_modules(category.id)
            for index, module in enumerate(modules):
                if module.id in existing_ids:
                    continue
                db.session.add(UserModuleProgress(
                    user_id=user.id, module_id=module.id,
                    unlocked=(index == 0), completed=False, bonus_awarded=False,
                ))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to initialize module progression for user %s", user.id
        )


def is_module_completed(user: User, module: RoadmapModule) -> bool:
    """True if this user's UserModuleProgress row for the module is completed."""
    if user is None or module is None:
        return False
    row = UserModuleProgress.query.filter_by(
        user_id=user.id, module_id=module.id, completed=True
    ).first()
    return row is not None


def module_status(user: User, module: RoadmapModule) -> str:
    """Per-user module status: completed | available | locked.

    Read from UserModuleProgress only — never from RoadmapModule.is_locked
    (deprecated). A missing row is treated as locked, except the first
    module of a category, which is implicitly available so the roadmap is
    never fully locked for a user whose rows predate a new module.
    """
    if module is None:
        return "locked"
    row = UserModuleProgress.query.filter_by(
        user_id=user.id, module_id=module.id
    ).first()
    if row is not None:
        if row.completed:
            return "completed"
        return "available" if row.unlocked else "locked"

    # No row yet: first module of the category is available, others locked.
    siblings = get_modules(module.category_id)
    if siblings and siblings[0].id == module.id:
        return "available"
    return "locked"


def lesson_locked_for_user(user: User, module: RoadmapModule, lesson: Lesson) -> bool:
    """True if this lesson may not be viewed or completed yet.

    Every lesson is gated by its module's per-user unlock status
    (``module_status``), with one deliberate exception: a preview lesson
    (``Lesson.is_preview`` — always the first lesson of a module, per
    ``seed.py``'s ``is_preview=(les_order == 1)``) is a sneak peek of the
    next module and stays viewable/completable even while its module is
    locked, matching how ``module.html`` already renders a live "Start
    Lesson" link for the preview lesson regardless of lock status.
    """
    if lesson.is_preview:
        return False
    return module_status(user, module) == "locked"


def is_lesson_locked(user: User, module_slug: str, lesson_slug: str) -> bool | None:
    """Whether a lesson is currently locked for this user.

    Returns ``None`` if the module or lesson doesn't exist (the caller
    should 404), otherwise the ``lesson_locked_for_user`` result.
    """
    module = get_module(module_slug)
    if module is None:
        return None
    lesson = get_lesson(module_slug, lesson_slug)
    if lesson is None:
        return None
    return lesson_locked_for_user(user, module, lesson)


def unlock_next_module(user: User, module: RoadmapModule) -> Optional[RoadmapModule]:
    """Unlock the next module in the same category for THIS user.

    Returns the newly-unlocked module (or None if there is no next module).
    Idempotent: if the next module is already unlocked, nothing changes and
    it is still returned for messaging. Caller commits.
    """
    if module is None:
        return None
    siblings = get_modules(module.category_id)
    index = next((i for i, m in enumerate(siblings) if m.id == module.id), None)
    if index is None or index + 1 >= len(siblings):
        return None

    nxt = siblings[index + 1]
    row = _get_or_create_module_progress(user, nxt)
    row.unlocked = True
    return nxt


def complete_module(user: User, module: RoadmapModule) -> dict[str, Any]:
    """Mark a module completed for a user and award its bonus XP once.

    Duplicate-safe via the ``bonus_awarded`` flag: XP is granted through
    award_xp() only on the first completion, and never again. Unlocks the
    next module for this user. Returns {awarded_xp, next_module,
    newly_completed}. Caller's surrounding transaction commits.
    """
    row = _get_or_create_module_progress(user, module)

    if row.completed and row.bonus_awarded:
        # Already fully processed — no XP, no re-unlock side effects.
        return {"awarded_xp": 0, "next_module": None, "newly_completed": False}

    awarded = 0
    if not row.bonus_awarded:
        award_xp(user, module.xp_reward)
        awarded = module.xp_reward
        row.bonus_awarded = True

    row.completed = True
    row.completed_at = _utcnow()

    nxt = unlock_next_module(user, module)
    return {"awarded_xp": awarded, "next_module": nxt, "newly_completed": True}


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def complete_lesson(user: User, module_slug: str, lesson_slug: str) -> dict[str, Any]:
    """Mark a lesson complete for a user, awarding XP exactly once.

    Returns a structured result:
        {success, already_completed, lesson, xp_awarded}

    - Missing lesson  -> success=False, lesson=None.
    - Already done    -> success=True, already_completed=True, xp_awarded=0,
                         and NO database changes.
    - First time      -> creates the progress row, awards lesson.xp_reward
                         through the existing award_xp() engine, commits.
    XP is never written to user.xp directly, and the unique
    (user_id, lesson_id) constraint guarantees one row per pair.
    """
    result = {
        "success": False,
        "already_completed": False,
        "lesson": None,
        "xp_awarded": 0,
        # Module-completion outcome (YC-007.0), populated on the transition.
        "module_completed": False,
        "module_xp_awarded": 0,
        "module_title": None,
        "unlocked_module_title": None,
    }

    lesson = get_lesson(module_slug, lesson_slug)
    if lesson is None:
        return result
    result["lesson"] = lesson

    # Idempotency: if a completed row exists, change nothing and award nothing.
    existing = UserLessonProgress.query.filter_by(
        user_id=user.id, lesson_id=lesson.id
    ).first()
    if existing is not None and existing.completed:
        result["success"] = True
        result["already_completed"] = True
        return result

    module = get_module(module_slug)

    try:
        if existing is None:
            existing = UserLessonProgress(user_id=user.id, lesson_id=lesson.id)
            db.session.add(existing)

        now = _utcnow()
        existing.completed = True
        existing.completed_at = now
        existing.last_opened = now
        existing.time_spent = existing.time_spent or 0
        existing.score = None

        # Award lesson XP through the engine (recalculates level + commits).
        award_xp(user, lesson.xp_reward)

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to complete lesson %s for user %s", lesson.id, user.id
        )
        return result

    result["success"] = True
    result["xp_awarded"] = lesson.xp_reward

    # --- Module-completion transition (YC-007.0 per-user) ------------------
    # Detect completion from the lessons (all lessons now done), then record
    # it in UserModuleProgress via complete_module(), which awards the bonus
    # once (bonus_awarded guard) and unlocks the next module for this user.
    if module is not None and _all_lessons_completed(user, module):
        already = UserModuleProgress.query.filter_by(
            user_id=user.id, module_id=module.id, completed=True
        ).first()
        if already is None:
            try:
                outcome = complete_module(user, module)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception(
                    "Failed to complete module %s for user %s", module.id, user.id
                )
                outcome = None

            if outcome and outcome["newly_completed"]:
                result["module_completed"] = True
                result["module_xp_awarded"] = outcome["awarded_xp"]
                result["module_title"] = module.title
                if outcome["next_module"] is not None:
                    result["unlocked_module_title"] = outcome["next_module"].title

    return result


def _all_lessons_completed(user: User, module: RoadmapModule) -> bool:
    """True if every lesson in the module has a completed progress row."""
    lessons = module.lessons
    if not lessons:
        return False
    done = len(_completed_lesson_ids(user, [l.id for l in lessons]))
    return done == len(lessons)


def _module_has_quiz(module_slug: str) -> bool:
    """Whether a module has an active quiz (delegates to quiz_services)."""
    from app.roadmap import quiz_services as qs
    return qs.get_module_quiz(module_slug) is not None


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
    # YC-022.0 perf: one batched completion lookup for the whole module
    # instead of one query per lesson.
    done_ids = _completed_lesson_ids(user, [l.id for l in lessons])
    lesson_views = [
        {
            "title": lesson.title,
            "slug": lesson.slug,
            "lesson_type": lesson.lesson_type,
            "estimated_minutes": lesson.estimated_minutes,
            "xp_reward": lesson.xp_reward,
            "is_preview": lesson.is_preview,
            "completed": lesson.id in done_ids,
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
            # Per-user status (YC-007.0); is_locked is deprecated.
            "status": module_status(user, module),
            # Whether this module has a quiz to take (YC-007.3).
            "has_quiz": _module_has_quiz(module_slug),
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
    # Ensure this user has module-progression rows (idempotent). Done here
    # rather than in the auth flow so authentication code stays untouched;
    # the first roadmap load after registration initializes progression,
    # unlocking each category's first module.
    initialize_user_progression(user)

    categories: list[dict[str, Any]] = []

    # ---- YC-022.0 perf: batch everything user-specific up front ----------
    # One query: every module-progress row for this user, keyed by module.
    progress_rows = {
        row.module_id: row
        for row in UserModuleProgress.query.filter_by(user_id=user.id).all()
    }
    # One computation (itself single-query now): per-category percent.
    category_progress = get_category_progress(user)
    # One query: every completed lesson id across the whole roadmap.
    all_lesson_ids: list[int] = []
    tree: list[tuple[Any, list[Any]]] = []
    for category in get_all_categories():
        modules = get_modules(category.id)
        tree.append((category, modules))
        for module in modules:
            # module.lessons is selectin-loaded and display_order-sorted.
            all_lesson_ids.extend(l.id for l in module.lessons)
    done_ids = _completed_lesson_ids(user, all_lesson_ids)

    def _status(module, index: int) -> str:
        """module_status(), but from the prefetched rows (same semantics)."""
        row = progress_rows.get(module.id)
        if row is not None:
            if row.completed:
                return "completed"
            return "available" if row.unlocked else "locked"
        return "available" if index == 0 else "locked"
    # ----------------------------------------------------------------------

    for category, modules in tree:
        category_lessons = 0
        module_views: list[dict[str, Any]] = []

        for index, module in enumerate(modules):
            lessons = list(module.lessons)
            category_lessons += len(lessons)
            done = sum(1 for l in lessons if l.id in done_ids)

            module_views.append({
                "title": module.title,
                "slug": module.slug,
                "difficulty": module.difficulty,
                "estimated_hours": module.estimated_hours,
                "xp_reward": module.xp_reward,
                # Per-user unlock/completion status (YC-007.0):
                # "available" | "locked" | "completed".
                "status": _status(module, index),
                "lesson_count": len(lessons),
                "progress_percent": _percent(done, len(lessons)),
                "lessons": [
                    {
                        "title": lesson.title,
                        "slug": lesson.slug,
                        "module_slug": module.slug,
                        "lesson_type": lesson.lesson_type,
                        "xp_reward": lesson.xp_reward,
                        "estimated_minutes": lesson.estimated_minutes,
                        "is_preview": lesson.is_preview,
                        "completed": lesson.id in done_ids,
                    }
                    for lesson in lessons
                ],
            })

        cat_progress = category_progress.get(category.id, 0)
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
        "roadmap_version": ROADMAP_VERSION,
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



# ---------------------------------------------------------------------------
# Quiz page contexts (YC-007.3) — compose the YC-007.2 services into plain
# dicts for the templates. No ORM objects leak to routes/templates.
# ---------------------------------------------------------------------------
def get_quiz_index_context(user: User) -> dict[str, Any]:
    """List every module's quiz with this user's status, for the index page."""
    from app.roadmap import quiz_services as qs

    quizzes: list[dict[str, Any]] = []
    for category in get_all_categories():
        for module in get_modules(category.id):
            quiz = qs.get_module_quiz(module.slug)
            if quiz is None:
                continue
            best = qs.get_best_attempt(user, quiz)
            quizzes.append({
                "module_title": module.title,
                "module_slug": module.slug,
                "category_title": category.title,
                "category_color": category.color,
                "quiz_title": quiz.title,
                "question_count": len(qs.get_quiz_questions(quiz)),
                "xp_reward": quiz.xp_reward,
                "pass_percentage": quiz.pass_percentage,
                "time_limit_minutes": quiz.time_limit_minutes,
                "passed": qs.has_passed_quiz(user, quiz),
                "best_percentage": best.percentage if best is not None else None,
                "attempt_count": len(qs.get_user_attempts(user, quiz)),
                "can_take": qs.can_take_quiz(user, module.slug),
            })
    return {"quizzes": quizzes, "nav_items": get_nav_items(active="quizzes")}


def _quiz_question_views(quiz: Quiz) -> list[dict[str, Any]]:
    """Questions + options as plain dicts (no is_correct leaked to the page)."""
    from app.roadmap import quiz_services as qs

    views: list[dict[str, Any]] = []
    for question in qs.get_quiz_questions(quiz):
        views.append({
            "id": question.id,
            "question_text": question.question_text,
            "options": [
                {"id": o.id, "option_text": o.option_text}
                for o in question.options
            ],
        })
    return views


def get_quiz_page_context(user: User, module_slug: str) -> Optional[dict[str, Any]]:
    """Context for the quiz-taking page, or None if the module/quiz is missing.

    Deliberately omits which option is correct — grading happens server
    side in submit_quiz, so answers are never exposed to the client.
    """
    from app.roadmap import quiz_services as qs

    module = get_module(module_slug)
    if module is None:
        return None
    quiz = qs.get_module_quiz(module_slug)
    if quiz is None:
        return None

    best = qs.get_best_attempt(user, quiz)
    latest = qs.get_latest_attempt(user, quiz)
    lesson_progress = get_module_progress(user, module)
    return {
        "module": {"title": module.title, "slug": module.slug},
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "xp_reward": quiz.xp_reward,
            "pass_percentage": quiz.pass_percentage,
            "time_limit_minutes": quiz.time_limit_minutes,
            "question_count": len(_quiz_question_views(quiz)),
        },
        "questions": _quiz_question_views(quiz),
        "passed": qs.has_passed_quiz(user, quiz),
        "best_percentage": best.percentage if best is not None else None,
        "latest_attempt": {
            "score": latest.score,
            "percentage": latest.percentage,
            "passed": latest.passed,
        } if latest is not None else None,
        "attempt_count": len(qs.get_user_attempts(user, quiz)),
        "can_take": qs.can_take_quiz(user, module_slug),
        # Lesson-completion progress for the locked screen.
        "lesson_progress": {
            "completed": lesson_progress["completed_lessons"],
            "total": lesson_progress["total_lessons"],
            "percent": lesson_progress["percent"],
        },
        "nav_items": get_nav_items(active="quizzes"),
    }
