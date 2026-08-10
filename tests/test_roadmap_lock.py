"""Tests for YC-036.2 — Roadmap Curriculum Lock.

Pins the structural invariants documented in docs/ROADMAP_LOCK.md: a
locked category/module/lesson hierarchy, deterministic ordering, no
duplicate slugs/ordering, no orphaned records, server-side lock
enforcement (fixed by this ticket), and that XP/progress stay intact
through the normal lesson-completion flow. Content quality (91 of 96
lessons still empty as of YC-036.3, gameable quizzes) is deliberately
NOT asserted as passing — see docs/ROADMAP_LOCK.md "Known Issues" —
only pinned as a baseline so new empty/placeholder lessons can't be
added silently. Python Programming's 3 lessons (YC-036.3) are the
first real content in the roadmap; this file also pins that they stay
real.
"""

from __future__ import annotations

import os
import tempfile
from typing import ClassVar

_TMPDIR = tempfile.mkdtemp(prefix="yc0362-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_roadmap.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from sqlalchemy.exc import IntegrityError

from app.roadmap.audit import audit_roadmap, format_audit_report


@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db

    a = create_app()
    a.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with a.app_context():
        db.create_all()
        # NOTE: this project's test suite shares one physical sqlite file
        # across every test module in a single pytest run — config.py
        # reads DATABASE_URL exactly once, as a class-body expression, the
        # first time any test file's create_app() triggers config.py's
        # import; every other module's own `os.environ["DATABASE_URL"] =
        # ...` line (set at collection time, before any test runs) is a
        # no-op as far as Flask config is concerned. seed_roadmap()'s
        # blanket "any category exists" idempotency guard can therefore
        # silently no-op here because of an unrelated category some other
        # test module created first. Ensure our own curriculum exists by
        # name rather than trusting that guard.
        from app.roadmap.models import RoadmapCategory
        from app.roadmap.seed import _insert_curriculum
        if RoadmapCategory.query.filter_by(title="Beginner").first() is None:
            _insert_curriculum()
    yield a


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db

    with app.app_context():
        u = User(username="roadmap_test", email="roadmap@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "roadmap_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


# The 4 categories docs/ROADMAP_LOCK.md locks — used to scope assertions to
# just the locked curriculum. This test suite shares one physical database
# across every test module in a single run (see the ``app`` fixture below),
# and a couple of unrelated files (test_analytics.py, test_community.py)
# create their own throwaway RoadmapCategory/Module/Lesson rows with
# low/colliding display_order values and non-curriculum lesson titles —
# real for their own purposes, irrelevant to (and must not perturb) the
# locked-curriculum invariants this file pins.
_LOCKED_CATEGORY_TITLES = ("Beginner", "Intermediate", "Red Team", "AI Security")


# ═══════════════════════════════════════════
# Deterministic ordering
# ═══════════════════════════════════════════
class TestOrdering:
    def test_categories_have_deterministic_ordering(self, app):
        from app.roadmap.models import RoadmapCategory
        with app.app_context():
            cats = (
                RoadmapCategory.query
                .filter(RoadmapCategory.title.in_(_LOCKED_CATEGORY_TITLES))
                .order_by(RoadmapCategory.display_order)
                .all()
            )
            assert len(cats) == 4
            orders = [c.display_order for c in cats]
            assert orders == sorted(orders)
            assert len(orders) == len(set(orders)), "duplicate category display_order"

    def test_modules_have_deterministic_ordering_within_category(self, app):
        from app.roadmap.services import get_all_categories, get_modules
        with app.app_context():
            for category in get_all_categories():
                modules = get_modules(category.id)
                orders = [m.display_order for m in modules]
                assert orders == sorted(orders)
                assert len(orders) == len(set(orders)), (
                    f"duplicate module display_order in category {category.id}")

    def test_lessons_have_deterministic_ordering_within_module(self, app):
        from app.roadmap.services import get_all_categories, get_lessons, get_modules
        with app.app_context():
            for category in get_all_categories():
                for module in get_modules(category.id):
                    lessons = get_lessons(module.id)
                    orders = [l.display_order for l in lessons]
                    assert orders == sorted(orders)
                    assert len(orders) == len(set(orders)), (
                        f"duplicate lesson display_order in module {module.id}")

    def test_seeded_module_order_matches_locked_spec(self, app):
        """Pins the exact Beginner module order documented in
        docs/ROADMAP_LOCK.md's 'Module Order' section."""
        from app.roadmap.services import get_modules

        with app.app_context():
            from app.roadmap.models import RoadmapCategory
            beginner = RoadmapCategory.query.filter_by(title="Beginner").first()
            slugs = [m.slug for m in get_modules(beginner.id)]
            assert slugs == [
                "linux-fundamentals", "computer-networking", "python-programming",
                "web-fundamentals", "git-github", "operating-systems",
                "cryptography-basics", "virtualization",
            ]

    def test_seeded_lesson_order_matches_locked_spec(self, app):
        """Every locked-curriculum module's 3 lessons follow the fixed
        introduction -> core-concepts -> hands-on-practice order."""
        from app.roadmap.models import RoadmapCategory
        from app.roadmap.services import get_lessons, get_modules

        with app.app_context():
            categories = (
                RoadmapCategory.query
                .filter(RoadmapCategory.title.in_(_LOCKED_CATEGORY_TITLES))
                .all()
            )
            assert len(categories) == 4
            for category in categories:
                for module in get_modules(category.id):
                    slugs = [l.slug for l in get_lessons(module.id)]
                    assert slugs == ["introduction", "core-concepts", "hands-on-practice"]


# ═══════════════════════════════════════════
# Duplicates prevented
# ═══════════════════════════════════════════
class TestDuplicatesPrevented:
    def test_duplicate_module_slug_rejected_by_schema(self, app):
        from app.extensions import db
        from app.roadmap.models import RoadmapCategory, RoadmapModule

        with app.app_context():
            category = RoadmapCategory.query.first()
            dupe = RoadmapModule(
                category_id=category.id, title="Duplicate", slug="linux-fundamentals",
                display_order=99,
            )
            db.session.add(dupe)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_duplicate_lesson_slug_within_module_rejected_by_schema(self, app):
        from app.extensions import db
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="linux-fundamentals").first()
            dupe = Lesson(
                module_id=module.id, title="Duplicate", slug="introduction",
                display_order=99,
            )
            db.session.add(dupe)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_audit_reports_zero_duplicates_on_seeded_data(self, app):
        with app.app_context():
            report = audit_roadmap()
            assert report["duplicate_module_slugs"] == []
            assert report["duplicate_lesson_slugs"] == []
            assert report["duplicate_module_ordering"] == []
            assert report["duplicate_lesson_ordering"] == []


# ═══════════════════════════════════════════
# Prerequisites
# ═══════════════════════════════════════════
class TestPrerequisites:
    def test_no_broken_prerequisites_reported(self, app):
        """No prerequisite_module_id column exists today (see
        docs/ROADMAP_LOCK.md) — the check is a structural no-op, and
        must stay that way until such a column is added."""
        with app.app_context():
            report = audit_roadmap()
            assert report["broken_prerequisites"] == []

    def test_module_only_unlocks_after_previous_in_same_category(self, app, student):
        """The real, documented dependency graph: linear within a
        category via UserModuleProgress, nothing cross-category."""
        from app.auth.models import User
        from app.roadmap.models import RoadmapCategory
        from app.roadmap.services import (
            get_modules,
            initialize_user_progression,
            module_status,
        )

        with app.app_context():
            user = User.query.filter_by(username="roadmap_test").first()
            initialize_user_progression(user)
            beginner = RoadmapCategory.query.filter_by(title="Beginner").first()
            modules = get_modules(beginner.id)
            assert module_status(user, modules[0]) == "available"
            assert module_status(user, modules[1]) == "locked"
            assert module_status(user, modules[2]) == "locked"


# ═══════════════════════════════════════════
# Published lessons / empty / placeholder content
# ═══════════════════════════════════════════
class TestContentBaseline:
    def test_published_lessons_matches_active_lesson_count(self, app):
        with app.app_context():
            report = audit_roadmap()
            assert report["published_lessons"] == report["lessons"]

    def test_empty_and_placeholder_counts_pinned_to_known_baseline(self, app):
        """Deliberately NOT asserting these are zero — content quality is
        explicit backlog (docs/ROADMAP_LOCK.md Known Issues #3/#4). This
        pins today's exact counts so a new lesson silently added without
        real content fails this test instead of going unnoticed.

        Scoped to the locked curriculum's own 4 categories rather than
        ``audit_roadmap()``'s whole-database counts: this test suite
        shares one physical database across every test module in a
        single run (see the ``app`` fixture above), and a couple of
        unrelated test files (test_analytics.py, test_community.py)
        create their own throwaway RoadmapCategory/Lesson rows for their
        own purposes — those must not perturb this pinned count.
        """
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapCategory, RoadmapModule

        with app.app_context():
            lessons = (
                Lesson.query
                .join(RoadmapModule, Lesson.module_id == RoadmapModule.id)
                .join(RoadmapCategory, RoadmapModule.category_id == RoadmapCategory.id)
                .filter(RoadmapCategory.title.in_(_LOCKED_CATEGORY_TITLES))
                .all()
            )
            assert len(lessons) == 96

            empty = sum(1 for lesson in lessons if _lesson_content_state(lesson)[0])
            placeholder = sum(1 for lesson in lessons if _lesson_content_state(lesson)[1])
            # 94 -> 91 as of YC-036.3: Python Programming's 3 lessons now
            # have real content (see TestPythonProgrammingContent below).
            assert empty == 91
            assert placeholder == 1

    def test_format_audit_report_is_stable_text(self, app):
        with app.app_context():
            text = format_audit_report(audit_roadmap())
            assert "Tracks:" in text
            assert "Modules:" in text
            assert "Lessons:" in text


# ═══════════════════════════════════════════
# Future modules never appear as active/published content
# ═══════════════════════════════════════════
class TestFutureModulesNotActive:
    def test_empty_category_reported_but_contributes_zero_modules(self, app):
        from app.extensions import db
        from app.roadmap.models import RoadmapCategory
        from app.roadmap.services import get_modules

        with app.app_context():
            future = RoadmapCategory(
                title="Future Track Placeholder", display_order=999, is_active=True,
            )
            db.session.add(future)
            db.session.commit()
            try:
                assert get_modules(future.id) == []
                report = audit_roadmap()
                assert "Future Track Placeholder" in report["empty_categories"]
            finally:
                db.session.delete(future)
                db.session.commit()

    def test_inactive_module_excluded_from_get_modules(self, app):
        from app.extensions import db
        from app.roadmap.models import RoadmapCategory, RoadmapModule
        from app.roadmap.services import get_modules

        with app.app_context():
            category = RoadmapCategory.query.first()
            inactive = RoadmapModule(
                category_id=category.id, title="Future Module", slug="future-module-yc0362",
                display_order=999, is_active=False,
            )
            db.session.add(inactive)
            db.session.commit()
            try:
                slugs = [m.slug for m in get_modules(category.id)]
                assert "future-module-yc0362" not in slugs
            finally:
                db.session.delete(inactive)
                db.session.commit()


# ═══════════════════════════════════════════
# Orphaned records
# ═══════════════════════════════════════════
class TestOrphans:
    def test_no_orphaned_modules_or_lessons_on_seeded_data(self, app):
        with app.app_context():
            report = audit_roadmap()
            assert report["orphaned_modules"] == []
            assert report["orphaned_lessons"] == []


# ═══════════════════════════════════════════
# Server-side lock enforcement (YC-036.2 fix)
# ═══════════════════════════════════════════
class TestLockEnforcement:
    def test_locked_non_preview_lesson_blocked_by_get(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/computer-networking/core-concepts/", follow_redirects=False)
            assert r.status_code == 302
            assert "/roadmap/computer-networking/" in r.headers["Location"]

    def test_locked_non_preview_lesson_blocked_by_complete_and_awards_no_xp(self, app, student):
        from app.auth.models import User

        uname, uid = student
        with app.app_context():
            xp_before = User.query.get(uid).xp
        with app.test_client() as c:
            _login(c, uname)
            r = c.post("/roadmap/computer-networking/core-concepts/complete", follow_redirects=False)
            assert r.status_code == 302
            assert "/roadmap/computer-networking/" in r.headers["Location"]
        with app.app_context():
            xp_after = User.query.get(uid).xp
        assert xp_after == xp_before

    def test_preview_lesson_of_locked_module_still_viewable(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/computer-networking/introduction/", follow_redirects=False)
            assert r.status_code == 200

    def test_preview_lesson_of_locked_module_still_completable(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.post("/roadmap/computer-networking/introduction/complete", follow_redirects=True)
            assert r.status_code == 200

    def test_unknown_lesson_still_404s(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/linux-fundamentals/does-not-exist/")
            assert r.status_code == 404
            r2 = c.post("/roadmap/linux-fundamentals/does-not-exist/complete")
            assert r2.status_code == 404

    def test_is_lesson_locked_service_helper(self, app, student):
        from app.auth.models import User
        from app.roadmap.services import is_lesson_locked

        with app.app_context():
            user = User.query.filter_by(username="roadmap_test").first()
            assert is_lesson_locked(user, "does-not-exist", "introduction") is None
            assert is_lesson_locked(user, "computer-networking", "core-concepts") is True
            assert is_lesson_locked(user, "computer-networking", "introduction") is False
            assert is_lesson_locked(user, "linux-fundamentals", "introduction") is False


# ═══════════════════════════════════════════
# Progress / XP remain correct through the real completion flow
# ═══════════════════════════════════════════
class TestProgressAndXP:
    def test_lesson_progress_created_on_completion(self, app):
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import UserLessonProgress
        from app.roadmap.services import complete_lesson

        with app.app_context():
            u = User(username="progress_test", email="progress@t.io")
            u.set_password("Str0ngPass!")
            db.session.add(u)
            db.session.commit()

            result = complete_lesson(u, "linux-fundamentals", "introduction")
            assert result["success"] is True
            assert result["xp_awarded"] == 25

            row = UserLessonProgress.query.filter_by(
                user_id=u.id, lesson_id=result["lesson"].id
            ).first()
            assert row is not None
            assert row.completed is True

    def test_completion_is_idempotent_no_double_xp(self, app):
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.services import complete_lesson

        with app.app_context():
            u = User(username="idempotent_test", email="idempotent@t.io")
            u.set_password("Str0ngPass!")
            db.session.add(u)
            db.session.commit()
            uid = u.id

            complete_lesson(u, "linux-fundamentals", "introduction")
            xp_after_first = User.query.get(uid).xp

            second = complete_lesson(User.query.get(uid), "linux-fundamentals", "introduction")
            assert second["already_completed"] is True
            assert second["xp_awarded"] == 0
            xp_after_second = User.query.get(uid).xp
            assert xp_after_second == xp_after_first

    def test_module_completion_awards_bonus_and_unlocks_next(self, app):
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule
        from app.roadmap.services import complete_lesson, module_status

        with app.app_context():
            u = User(username="module_complete_test", email="module_complete@t.io")
            u.set_password("Str0ngPass!")
            db.session.add(u)
            db.session.commit()
            uid = u.id

            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                complete_lesson(User.query.get(uid), "linux-fundamentals", slug)

            xp = User.query.get(uid).xp
            # 25 + 50 + 100 lesson XP + 175 module bonus = 350
            assert xp == 350

            next_module = RoadmapModule.query.filter_by(slug="computer-networking").first()
            assert module_status(User.query.get(uid), next_module) == "available"

    def test_category_progress_percent_reflects_completions(self, app):
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapCategory
        from app.roadmap.services import complete_lesson, get_category_progress

        with app.app_context():
            u = User(username="category_progress_test", email="category_progress@t.io")
            u.set_password("Str0ngPass!")
            db.session.add(u)
            db.session.commit()
            uid = u.id

            beginner = RoadmapCategory.query.filter_by(title="Beginner").first()
            before = get_category_progress(User.query.get(uid))[beginner.id]
            assert before == 0

            complete_lesson(User.query.get(uid), "linux-fundamentals", "introduction")
            after = get_category_progress(User.query.get(uid))[beginner.id]
            assert after > before


# ═══════════════════════════════════════════
# Python Programming lesson content (YC-036.3)
# ═══════════════════════════════════════════
class TestPythonProgrammingContent:
    """Guards the real content written for YC-036.3 — not just that a
    file exists, but that each lesson still contains its actual taught
    material and isn't quietly regressed back to a stub."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "interpreted", "REPL", "IndentationError", "print(",
            "statement", "expression",
        ],
        "core-concepts": [
            "dynamic typing", "NoneType", "f-string", "type(",
            "ValueError", "snake_case",
        ],
        "hands-on-practice": [
            "elif", "range(", "break", "continue", "return",
            "is_strong", "local",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/beginner/python-programming/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
            # A real, hand-written lesson at this scope is well over 1KB
            # of rendered HTML; a stub or "coming soon" placeholder is not.
            assert len(html) > 3000, f"{slug}: suspiciously short ({len(html)} chars)"

    def test_lessons_contain_their_taught_terms(self, app):
        for slug, terms in self._EXPECTED_TERMS.items():
            html = self._render(app, slug)
            for term in terms:
                assert term in html, f"{slug}: missing expected term {term!r}"

    def test_lessons_contain_real_code_examples(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert "<pre>" in html and "<code>" in html, f"{slug}: no code block rendered"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="python-programming").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        """The introduction lesson is a preview and always reachable;
        core-concepts and hands-on-practice require the module unlocked
        (YC-036.2's lock enforcement) — unlock it the same way normal
        progression would, then confirm all three actually serve the
        real content, not the "coming soon" fallback."""
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="python-programming").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/python-programming/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body


# ═══════════════════════════════════════════
# HTTP — roadmap pages still reachable, CyberMentor/labs/missions unaffected
# ═══════════════════════════════════════════
class TestHTTP:
    def test_roadmap_index_reachable(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "Python Programming" in body
            assert "Curriculum v1.0" in body

    def test_labs_index_still_reachable(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/labs/")
            assert r.status_code == 200

    def test_missions_index_still_reachable(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/interactive-labs")
            assert r.status_code == 200
