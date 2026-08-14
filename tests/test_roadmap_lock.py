"""Tests for YC-036.2 — Roadmap Curriculum Lock.

Pins the structural invariants documented in docs/ROADMAP_LOCK.md: a
locked category/module/lesson hierarchy, deterministic ordering, no
duplicate slugs/ordering, no orphaned records, server-side lock
enforcement (fixed by this ticket), and that XP/progress stay intact
through the normal lesson-completion flow. Content quality (57 of 96
lessons still empty as of YC-037.5, gameable quizzes) is deliberately
NOT asserted as passing — see docs/ROADMAP_LOCK.md "Known Issues" —
only pinned as a baseline so new empty/placeholder lessons can't be
added silently. Python Programming (YC-036.3), Linux Fundamentals
(YC-036.4), Computer Networking (YC-036.5), Web Fundamentals
(YC-036.6), Cryptography Basics / Cybersecurity Fundamentals
(YC-036.7), Git & GitHub (YC-036.8), Operating Systems (YC-036.9),
Virtualization (YC-037.0 — completing the Beginner category), Nmap
(YC-037.1 — the first real module in Intermediate), Wireshark
(YC-037.2), Burp Suite (YC-037.3), OWASP Top 10 (YC-037.4) and Active
Directory Basics (YC-037.5) are the real content in the roadmap; this
file also pins that all thirteen stay real.
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
        # Same reasoning as above, for the lab rows TestWebFundamentalsContent
        # checks (YC-036.6): seed_labs() is normally only run via the
        # `flask seed-labs` CLI command, not automatically in create_app().
        # Other test modules (e.g. test_cloud_lab.py) happen to call it on
        # the shared physical sqlite file, but this file must not depend on
        # collection order/another module running first — seed it here,
        # by name, exactly like the curriculum guard above.
        from app.labs.models import Lab
        if Lab.query.filter_by(slug="websec-http").first() is None:
            from app.labs.seed import seed_labs
            seed_labs()
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
            # 94 -> 91 as of YC-036.3 (Python Programming's 3 lessons), then
            # 91 -> 89 as of YC-036.4 (Linux Fundamentals' core-concepts and
            # hands-on-practice; its introduction lesson already had real
            # content before YC-036.3), then 89 -> 87 as of YC-036.5:
            # Computer Networking's core-concepts and hands-on-practice
            # were EMPTY, and its introduction was the one PLACEHOLDER
            # lesson (a leftover XSS test payload — see Known Issues #3b)
            # — all 3 are real now, so placeholder drops to 0. Then 87 ->
            # 84 as of YC-036.6: Web Fundamentals' all 3 lessons were
            # EMPTY (no content file at all). Then 84 -> 81 as of
            # YC-036.7: Cryptography Basics' all 3 lessons were EMPTY.
            # Then 81 -> 78 as of YC-036.8: Git & GitHub's all 3 lessons
            # were EMPTY. Then 78 -> 75 as of YC-036.9: Operating
            # Systems' all 3 lessons were EMPTY. See
            # TestNetworkingFundamentalsContent /
            # TestWebFundamentalsContent / TestCybersecurityFundamentalsContent /
            # TestGitGithubContent / TestOperatingSystemsContent below.
            # Then 75 -> 72 as of YC-037.0: Virtualization's all 3
            # lessons were EMPTY — the last EMPTY module in the Beginner
            # category, which is now complete. See
            # TestVirtualizationContent below. Then 72 -> 69 as of
            # YC-037.1: Nmap's all 3 lessons were EMPTY — the first real
            # module in Intermediate. See TestNmapContent below. Then
            # 69 -> 66 as of YC-037.2: Wireshark's all 3 lessons were
            # EMPTY. See TestWiresharkContent below. Then 66 -> 63 as of
            # YC-037.3: Burp Suite's all 3 lessons were EMPTY. See
            # TestBurpSuiteContent below. Then 63 -> 60 as of YC-037.4:
            # OWASP Top 10's all 3 lessons were EMPTY. See
            # TestOwaspTop10Content below. Then 60 -> 57 as of
            # YC-037.5: Active Directory Basics' all 3 lessons were
            # EMPTY. See TestActiveDirectoryContent below.
            assert empty == 57
            assert placeholder == 0

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
# Linux Fundamentals lesson content (YC-036.4)
# ═══════════════════════════════════════════
class TestLinuxFundamentalsContent:
    """Guards the real content written for YC-036.4 — not just that a
    file exists, but that each lesson still contains its actual taught
    material and isn't quietly regressed back to a stub. Also guards the
    lesson -> terminal/mission cross-links wired in this ticket."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "pwd", "whoami", "working directory", "hidden", "/etc", "/home",
        ],
        "core-concepts": [
            "absolute path", "relative path", "cd ..", "cat", "~",
        ],
        "hands-on-practice": [
            "chmod", "rwx", "least privilege", "mkdir", "rm -r", "Linux Basics",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/beginner/linux-fundamentals/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
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

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="linux-fundamentals").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="linux-fundamentals").first()
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [l.slug for l in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [l.xp_reward for l in lessons] == [25, 50, 100]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_practice_links_only_on_hands_on_practice(self, app, student):
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, expect_mission in (
                ("introduction", False),
                ("core-concepts", False),
                ("hands-on-practice", True),
            ):
                ctx = get_lesson_view_context(student_user, "linux-fundamentals", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert practice.get("show_terminal") is True
                assert bool(practice.get("mission_slug")) is expect_mission

    def test_terminal_and_mission_links_point_to_real_routes(self, app):
        with app.test_request_context():
            from flask import url_for
            # Must not raise — these are the exact endpoints lesson.html calls.
            assert url_for("terminal.terminal_page") == "/terminal"
            assert url_for("terminal.mission_page", slug="linux-basics") == (
                "/terminal/mission/linux-basics"
            )

    def test_linux_basics_mission_still_exists_and_is_reused_not_duplicated(self, app):
        from app.core.missions.mission_loader import MISSIONS
        assert "linux-basics" in MISSIONS
        mission = MISSIONS["linux-basics"]
        assert mission["title"] == "Linux Basics"
        objective_commands = {o["validate"]["match"] for o in mission["objectives"]}
        assert {"pwd", "ls", "ls -la", "history"} <= objective_commands

    def test_lesson_pages_render_over_http(self, app, student):
        """linux-fundamentals is the first module of the first category,
        unlocked automatically for every user — no manual unlock needed,
        unlike python-programming in the equivalent YC-036.3 test."""
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/linux-fundamentals/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body
            # Practice CTA only appears where the service context provides it.
            r = c.get("/roadmap/linux-fundamentals/hands-on-practice/")
            body = r.data.decode("utf-8")
            assert "Try it in the Terminal" in body
            assert "Linux Basics Mission" in body

    def test_cybermentor_receives_lesson_context(self, app, student):
        """The CyberMentor include reads `current_lab`, set in lesson.html
        to "<module title> — <lesson title>" (YC-036.4) — confirm it
        actually reaches the rendered page's mentor data attribute."""
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/linux-fundamentals/introduction/")
            body = r.data.decode("utf-8")
            assert 'data-mentor-lab="Linux Fundamentals' in body
            assert "Introduction" in body


# ═══════════════════════════════════════════
# Computer Networking lesson content (YC-036.5)
# ═══════════════════════════════════════════
class TestNetworkingFundamentalsContent:
    """Guards the real content written for YC-036.5 — not just that a
    file exists, but that each lesson still contains its actual taught
    material and isn't quietly regressed back to a stub or the leftover
    XSS test payload it replaced. Also guards the lesson -> mission
    cross-links wired in this ticket."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "client", "server", "MAC", "protocol", "packet loss",
        ],
        "core-concepts": [
            "CIDR", "broadcast address", "socket", "192.168.1.64/26",
            "well-known ports",
        ],
        "hands-on-practice": [
            "SYN-ACK", "NXDOMAIN", "default gateway", "ip route", "ss",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/beginner/computer-networking/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
            assert len(html) > 3000, f"{slug}: suspiciously short ({len(html)} chars)"

    def test_leftover_xss_payload_is_gone(self, app):
        """Known Issues #3b: introduction.md used to be a raw
        <script>alert(1)</script> test fixture. Confirm it's gone, not
        just that bleach still neutralizes it."""
        html = self._render(app, "introduction")
        assert "alert(1)" not in html
        assert "onclick" not in html.lower()

    def test_lessons_contain_their_taught_terms(self, app):
        for slug, terms in self._EXPECTED_TERMS.items():
            html = self._render(app, slug)
            for term in terms:
                assert term in html, f"{slug}: missing expected term {term!r}"

    def test_lessons_contain_real_code_examples(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert "<pre>" in html and "<code>" in html, f"{slug}: no code block rendered"

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="computer-networking").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="computer-networking").first()
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [l.slug for l in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [l.xp_reward for l in lessons] == [25, 50, 100]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_practice_links_scoped_to_commands_that_actually_work(self, app, student):
        """The free-practice terminal (`/terminal`) never attaches a
        simulated network to the shell — only the mission runner does —
        so networking lessons must NOT offer that link (it would send
        students to run `ping`/`ip`/`ss`/`nslookup` somewhere those
        commands fail). Only the real mission link should appear, and
        only on the two lessons that actually teach commands."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, expect_mission in (
                ("introduction", True),
                ("core-concepts", False),
                ("hands-on-practice", True),
            ):
                ctx = get_lesson_view_context(student_user, "computer-networking", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert "show_terminal" not in practice
                assert bool(practice.get("mission_slug")) is expect_mission
                if expect_mission:
                    assert practice["mission_slug"] == "networking-fundamentals"

    def test_mission_link_points_to_a_real_route_and_real_mission(self, app):
        with app.test_request_context():
            from flask import url_for
            assert url_for("terminal.mission_page", slug="networking-fundamentals") == (
                "/terminal/mission/networking-fundamentals"
            )
        from app.core.missions.mission_loader import MISSIONS
        assert "networking-fundamentals" in MISSIONS
        mission = MISSIONS["networking-fundamentals"]
        assert mission["title"] == "Networking Fundamentals"
        objective_commands = {o["validate"]["match"] for o in mission["objectives"]}
        assert {"ip addr", "ip route", "ss"} <= objective_commands

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        """introduction is a preview and always reachable; core-concepts
        and hands-on-practice require the module unlocked."""
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="computer-networking").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/computer-networking/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body
            r = c.get("/roadmap/computer-networking/hands-on-practice/")
            body = r.data.decode("utf-8")
            assert "Networking Fundamentals Mission" in body
            assert "Try it in the Terminal" not in body

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/computer-networking/introduction/")
            body = r.data.decode("utf-8")
            assert 'data-mentor-lab="Computer Networking' in body
            assert "Introduction" in body


# ═══════════════════════════════════════════
# Web Fundamentals lesson content (YC-036.6)
# ═══════════════════════════════════════════
class TestWebFundamentalsContent:
    """Guards the real content written for YC-036.6 — mirrors
    TestNetworkingFundamentalsContent's discipline: not just that a file
    exists, but that each lesson still contains its actual taught
    material, and that the lesson -> mission/lab cross-links wired in
    this ticket keep pointing at real routes."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "scheme", "fragment", "client-side", "Content-Security-Policy",
        ],
        "core-concepts": [
            "401 Unauthorized", "403 Forbidden",
            "application/x-www-form-urlencoded", "Cache-Control",
        ],
        "hands-on-practice": [
            "Set-Cookie", "HttpOnly", "SameSite", "Bearer training-token-001",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/beginner/web-fundamentals/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
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

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="web-fundamentals").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="web-fundamentals").first()
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [l.slug for l in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [l.xp_reward for l in lessons] == [25, 50, 100]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_practice_links_scoped_to_commands_that_actually_work(self, app, student):
        """The free-practice terminal (`/terminal`) never attaches a
        simulated web app to the shell (only the mission runner does —
        see `MissionRunner._attach_web_lab`), so web-fundamentals lessons
        must NOT offer that link. All three lessons use `open`/`headers`/
        `cookies`/`response` directly, so all three get the mission link;
        only core-concepts and hands-on-practice additionally get a
        reinforcing-lab link, matched to their actual content."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            expected_labs = {
                "introduction": None,
                "core-concepts": "websec-http",
                "hands-on-practice": "websec-cookies",
            }
            for slug, expected_lab in expected_labs.items():
                ctx = get_lesson_view_context(student_user, "web-fundamentals", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert "show_terminal" not in practice
                assert practice.get("mission_slug") == "web-fundamentals"
                assert practice.get("lab_slug") == expected_lab

    def test_mission_link_points_to_a_real_route_and_real_mission(self, app):
        with app.test_request_context():
            from flask import url_for
            assert url_for("terminal.mission_page", slug="web-fundamentals") == (
                "/terminal/mission/web-fundamentals"
            )
        from app.core.missions.mission_loader import MISSIONS
        assert "web-fundamentals" in MISSIONS
        mission = MISSIONS["web-fundamentals"]
        assert mission["title"] == "Web Fundamentals"
        objective_ids = {o["id"] for o in mission["objectives"]}
        assert {"wb-1", "wb-6", "wb-9", "wb-12"} <= objective_ids

    def test_lab_links_point_to_real_routes_and_real_labs(self, app):
        with app.test_request_context():
            from flask import url_for
            assert url_for("labs.detail", slug="websec-http") == "/labs/websec-http"
            assert url_for("labs.detail", slug="websec-cookies") == "/labs/websec-cookies"
        with app.app_context():
            from app.labs.models import Lab
            http_lab = Lab.query.filter_by(slug="websec-http").first()
            cookies_lab = Lab.query.filter_by(slug="websec-cookies").first()
            assert http_lab is not None and http_lab.is_active
            assert cookies_lab is not None and cookies_lab.is_active

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        """introduction is a preview and always reachable; core-concepts
        and hands-on-practice require the module unlocked."""
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="web-fundamentals").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/web-fundamentals/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body
                assert "Web Fundamentals Mission" in body
                assert "Try it in the Terminal" not in body
            r = c.get("/roadmap/web-fundamentals/core-concepts/")
            assert "HTTP Requests &amp; Responses Lab" in r.data.decode("utf-8")
            r = c.get("/roadmap/web-fundamentals/hands-on-practice/")
            assert "Cookie Security Flags Lab" in r.data.decode("utf-8")

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/web-fundamentals/introduction/")
            body = r.data.decode("utf-8")
            assert 'data-mentor-lab="Web Fundamentals' in body
            assert "Introduction" in body


# ═══════════════════════════════════════════
# Cryptography Basics / Cybersecurity Fundamentals lesson content (YC-036.7)
# ═══════════════════════════════════════════
class TestCybersecurityFundamentalsContent:
    """Guards the real content written for YC-036.7 — not just that a
    file exists, but that each lesson still contains its actual taught
    material and isn't quietly regressed back to a stub. Unlike Web
    Fundamentals, no lab or mission genuinely reinforces this module's
    content (no crypto/security-fundamentals lab or mission exists on
    this platform — see docs/ROADMAP_LOCK.md's audited Lab/Mission
    Mapping), so this module's ``practice`` context is expected to stay
    empty rather than gaining a fabricated link."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "CIA triad", "confidentiality", "operational security",
            "Asset → Threat → Vulnerability", "security mindset",
        ],
        "core-concepts": [
            "least privilege", "attack surface", "Authorization",
            "defense in depth", "threat actor",
        ],
        "hands-on-practice": [
            "rainbow table", "digital signature", "ransomware",
            "credential stuffing", "YushaBank",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/beginner/cryptography-basics/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
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

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="cryptography-basics").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="cryptography-basics").first()
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [l.slug for l in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [l.xp_reward for l in lessons] == [25, 50, 100]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_no_fabricated_lab_or_mission_links(self, app, student):
        """No real lab or mission exists for this module's subject
        matter (see docs/ROADMAP_LOCK.md's audited inventory) — the
        practice context must stay empty rather than pointing at a
        guessed/unrelated lab or mission."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                ctx = get_lesson_view_context(student_user, "cryptography-basics", slug)
                assert ctx is not None
                assert ctx["practice"] == {}

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        """introduction is a preview and always reachable; core-concepts
        and hands-on-practice require the module unlocked (this is the
        7th module in the Beginner category, not auto-unlocked)."""
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="cryptography-basics").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/cryptography-basics/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, _uid = student
        with app.app_context():
            from app.auth.models import User
            from app.extensions import db
            from app.roadmap.models import RoadmapModule, UserModuleProgress
            module = RoadmapModule.query.filter_by(slug="cryptography-basics").first()
            u = User.query.filter_by(username=uname).first()
            row = UserModuleProgress.query.filter_by(user_id=u.id, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=u.id, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/cryptography-basics/introduction/")
            body = r.data.decode("utf-8")
            assert 'data-mentor-lab="Cryptography Basics' in body
            assert "Introduction" in body


# ═══════════════════════════════════════════
# Git & GitHub lesson content (YC-036.8)
# ═══════════════════════════════════════════
class TestGitGithubContent:
    """Guards the real content written for YC-036.8 — not just that a
    file exists, but that each lesson still contains its actual taught
    material and isn't quietly regressed back to a stub. Like
    Cryptography Basics (YC-036.7), no lab or mission genuinely
    reinforces this module: the platform's terminal simulator has no
    `git` command (see app/core/terminal/commands.py's @cmd registry),
    so the practice context is expected to stay empty rather than
    gaining a fabricated link."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "Untracked files", "staging area", "root-commit", "Git is a program",
        ],
        "core-concepts": [
            "git diff --staged", "Fast-forward", "merge conflict", ".gitignore",
        ],
        "hands-on-practice": [
            "git clone", "pull request", "rotating the credential", "feature-branch",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/beginner/git-github/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
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

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="git-github").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="git-github").first()
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [l.slug for l in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [l.xp_reward for l in lessons] == [25, 50, 100]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_no_fabricated_lab_or_mission_links(self, app, student):
        """No real lab or mission exists for Git/GitHub on this
        platform (no `git` terminal command, no matching lab category)
        — the practice context must stay empty rather than pointing at
        a guessed/unrelated lab or mission."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                ctx = get_lesson_view_context(student_user, "git-github", slug)
                assert ctx is not None
                assert ctx["practice"] == {}

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        """introduction is a preview and always reachable; core-concepts
        and hands-on-practice require the module unlocked (this is the
        5th module in the Beginner category, not auto-unlocked)."""
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="git-github").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/git-github/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, _uid = student
        with app.app_context():
            from app.auth.models import User
            from app.extensions import db
            from app.roadmap.models import RoadmapModule, UserModuleProgress
            module = RoadmapModule.query.filter_by(slug="git-github").first()
            u = User.query.filter_by(username=uname).first()
            row = UserModuleProgress.query.filter_by(user_id=u.id, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=u.id, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/git-github/introduction/")
            body = r.data.decode("utf-8")
            # Jinja auto-escapes "&" to "&amp;" in the rendered attribute.
            assert 'data-mentor-lab="Git &amp; GitHub' in body
            assert "Introduction" in body


# ═══════════════════════════════════════════
# Operating Systems lesson content (YC-036.9)
# ═══════════════════════════════════════════
class TestOperatingSystemsContent:
    """Guards the real content written for YC-036.9 — not just that a
    file exists, but that each lesson still contains its actual taught
    material and isn't quietly regressed back to a stub. Unlike
    Cryptography Basics (YC-036.7) and Git & GitHub (YC-036.8), this
    module DOES get real lab/mission/terminal links — the Processes lab
    and Linux Permissions mission were real, existing, and unused by
    any other lesson; both are verified here rather than assumed."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "user space", "kernel space", "system call",
        ],
        "core-concepts": [
            "context switch", "virtual memory", "concurrency", "parallelism",
        ],
        "hands-on-practice": [
            "device driver", "daemon", "uid=1000(student)",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/beginner/operating-systems/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
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

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="operating-systems").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="operating-systems").first()
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [l.slug for l in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [l.xp_reward for l in lessons] == [25, 50, 100]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_practice_links_match_real_wired_resources(self, app, student):
        """introduction and core-concepts both offer the free-practice
        terminal (this module's `whoami`/`id`/`groups`/`uname` commands
        all work in the bare sandbox); only hands-on-practice also gets
        the real Linux Permissions mission and Processes lab — matched
        by actual content, not guessed."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, expect_mission_and_lab in (
                ("introduction", False),
                ("core-concepts", False),
                ("hands-on-practice", True),
            ):
                ctx = get_lesson_view_context(student_user, "operating-systems", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert practice.get("show_terminal") is True
                assert bool(practice.get("mission_slug")) is expect_mission_and_lab
                assert bool(practice.get("lab_slug")) is expect_mission_and_lab
                if expect_mission_and_lab:
                    assert practice["mission_slug"] == "linux-permissions"
                    assert practice["lab_slug"] == "linux-processes"

    def test_mission_and_lab_links_point_to_real_routes_and_real_resources(self, app):
        with app.test_request_context():
            from flask import url_for
            assert url_for("terminal.mission_page", slug="linux-permissions") == (
                "/terminal/mission/linux-permissions"
            )
            assert url_for("labs.detail", slug="linux-processes") == "/labs/linux-processes"
        from app.core.missions.mission_loader import MISSIONS
        assert "linux-permissions" in MISSIONS
        mission = MISSIONS["linux-permissions"]
        assert mission["title"] == "Linux Permissions"
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug="linux-processes").first()
            assert lab is not None and lab.is_active and lab.is_interactive
            assert lab.title == "Processes"

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        """introduction is a preview and always reachable; core-concepts
        and hands-on-practice require the module unlocked (this is the
        6th module in the Beginner category, not auto-unlocked)."""
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="operating-systems").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/operating-systems/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body
            r = c.get("/roadmap/operating-systems/hands-on-practice/")
            body = r.data.decode("utf-8")
            assert "Linux Permissions Mission" in body
            assert "Processes Lab" in body

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, uid = student
        with app.app_context():
            from app.extensions import db
            from app.roadmap.models import RoadmapModule, UserModuleProgress
            module = RoadmapModule.query.filter_by(slug="operating-systems").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/operating-systems/introduction/")
            body = r.data.decode("utf-8")
            assert 'data-mentor-lab="Operating Systems' in body
            assert "Introduction" in body


# ═══════════════════════════════════════════
# Virtualization — real content (YC-037.0)
# ═══════════════════════════════════════════
class TestVirtualizationContent:
    """Guards the real content written for YC-037.0 — the last EMPTY
    Beginner module. Pins not just that files exist but that each lesson
    still teaches its actual material, that the module's one genuine lab
    cross-link (Cloud Basics, the only place on this platform showing
    real VMs) resolves to a real route and a real lab row, and that
    `virtualization` deliberately gets NO free-practice terminal link —
    the terminal has no hypervisor/VM command at all."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "hypervisor", "host", "guest", "virtual machine",
        ],
        "core-concepts": [
            "Type 1", "Type 2", "vCPU", "overcommitment", "contention",
            "bridged", "host-only", "NAT",
        ],
        "hands-on-practice": [
            "snapshot", "container", "VM escape", "list-vms",
        ],
    }

    # Claims this module must never quietly lose — each one is a
    # correction of a specific, common misconception the driving ticket
    # named explicitly. Substring-matched against the rendered HTML.
    _REQUIRED_CORRECTIONS: ClassVar[dict[str, list[str]]] = {
        "core-concepts": [
            # a vCPU is not a reserved physical core
            "not a physical core reserved",
            # configuring memory does not create memory
            "does not create 24 GB of RAM",
        ],
        "hands-on-practice": [
            # a snapshot is not a backup
            "A Snapshot Is Not a Backup",
            # VM isolation is not absolute
            "not an absolute guarantee",
            # containers are not small VMs
            "shares the host",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/beginner/virtualization/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
            assert len(html) > 3000, f"{slug}: suspiciously short ({len(html)} chars)"

    def test_lessons_contain_their_taught_terms(self, app):
        for slug, terms in self._EXPECTED_TERMS.items():
            html = self._render(app, slug)
            for term in terms:
                assert term in html, f"{slug}: missing expected term {term!r}"

    def test_lessons_keep_their_misconception_corrections(self, app):
        """The claims this module exists to correct — a vCPU isn't a
        reserved core, configured RAM isn't new RAM, a snapshot isn't a
        backup, VM isolation isn't absolute, a container isn't a small
        VM. Losing any of these would make the module technically wrong,
        not merely thinner."""
        for slug, claims in self._REQUIRED_CORRECTIONS.items():
            html = self._render(app, slug)
            for claim in claims:
                assert claim in html, f"{slug}: lost required correction {claim!r}"

    def test_lessons_contain_real_code_examples(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert "<pre>" in html and "<code>" in html, f"{slug}: no code block rendered"

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="virtualization").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2,
        and the module still sits at Beginner display_order 8."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="virtualization").first()
            assert module.display_order == 8
            assert module.xp_reward == 175
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [l.slug for l in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [l.display_order for l in lessons] == [1, 2, 3]
            assert [l.xp_reward for l in lessons] == [25, 50, 100]
            assert [l.estimated_minutes for l in lessons] == [10, 20, 30]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_practice_links_scoped_to_hands_on_only_and_no_terminal_link(self, app, student):
        """Only hands-on-practice links out, and only to the Cloud Basics
        lab. No lesson offers the free-practice terminal: nothing this
        module teaches exists as a terminal command, so that CTA would
        send students somewhere none of it works."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, expect_lab in (
                ("introduction", False),
                ("core-concepts", False),
                ("hands-on-practice", True),
            ):
                ctx = get_lesson_view_context(student_user, "virtualization", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert not practice.get("show_terminal")
                assert not practice.get("mission_slug")
                assert bool(practice.get("lab_slug")) is expect_lab
                if expect_lab:
                    assert practice["lab_slug"] == "cloud-orientation"

    def test_lab_link_points_to_a_real_route_and_a_real_lab(self, app):
        with app.test_request_context():
            from flask import url_for
            assert url_for("labs.detail", slug="cloud-orientation") == (
                "/labs/cloud-orientation"
            )
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug="cloud-orientation").first()
            assert lab is not None and lab.is_active and lab.is_interactive
            assert lab.title == "Cloud Basics: Tour the Account"

    def test_quoted_lab_output_matches_the_real_simulator(self, app):
        """Section 12 quotes `list-vms` / `get-vm` output verbatim. If the
        cloud lab's VM inventory or formatting ever changes, the lesson
        becomes fabricated output — fail here rather than ship a lie."""
        from app.labs.cloud import engine
        from app.labs.cloud.accounts import YUSHACLOUD_PROD

        deployment = engine.build_deployment(YUSHACLOUD_PROD)
        vm_table = engine.format_vm_table(deployment)
        web01 = engine.format_vm(deployment, engine.find_vm(deployment, "web-01"))
        app01 = engine.format_vm(deployment, engine.find_vm(deployment, "app-01"))

        raw = self._raw_lesson("hands-on-practice")
        for block in (vm_table, web01, app01):
            for line in block.splitlines():
                assert line in raw, f"lesson no longer matches real lab output: {line!r}"

    @staticmethod
    def _raw_lesson(slug):
        from pathlib import Path

        import app as app_pkg
        path = (Path(app_pkg.__file__).parent / "content" / "roadmap"
                / "beginner" / "virtualization" / f"{slug}.md")
        return path.read_text(encoding="utf-8")

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        """introduction is a preview and always reachable; core-concepts
        and hands-on-practice require the module unlocked (this is the
        8th and last module in the Beginner category)."""
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="virtualization").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/virtualization/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body
            r = c.get("/roadmap/virtualization/hands-on-practice/")
            body = r.data.decode("utf-8")
            assert "Cloud Basics: Tour the Account Lab" in body
            # No terminal/mission CTA anywhere in this module.
            r = c.get("/roadmap/virtualization/introduction/")
            body = r.data.decode("utf-8")
            assert "Try it in the Terminal" not in body

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, uid = student
        with app.app_context():
            from app.extensions import db
            from app.roadmap.models import RoadmapModule, UserModuleProgress
            module = RoadmapModule.query.filter_by(slug="virtualization").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/virtualization/core-concepts/")
            body = r.data.decode("utf-8")
            assert 'data-mentor-lab="Virtualization' in body
            assert "Core Concepts" in body

    def test_completion_awards_xp_exactly_once(self, app, student):
        """Completing a Virtualization lesson awards its XP once; a
        repeat POST (the refresh case) must not award it again."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="virtualization").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()
            before = User.query.get(uid).xp

        with app.test_client() as c:
            _login(c, uname)
            c.post("/roadmap/virtualization/core-concepts/complete", follow_redirects=True)
            with app.app_context():
                after_first = User.query.get(uid).xp
            c.post("/roadmap/virtualization/core-concepts/complete", follow_redirects=True)
            with app.app_context():
                after_second = User.query.get(uid).xp

        assert after_first == before + 50, "core-concepts should award exactly 50 XP"
        assert after_second == after_first, "XP awarded twice for one lesson"


# ═══════════════════════════════════════════
# Nmap — real content (YC-037.1)
# ═══════════════════════════════════════════
class TestNmapContent:
    """Guards the real content written for YC-037.1 — the first real
    module in Intermediate. Pins not just that files exist but that
    each lesson teaches its actual material, that every quoted scan
    output is byte-for-byte what this platform's real Nmap simulator
    (`app/core/terminal/commands.py::_nmap`) actually produces against
    the real Nmap Fundamentals mission network, and that the module's
    lab (`nmap-basics`) and mission (`nmap-fundamentals`) links are
    real routes scoped to `hands-on-practice` only."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "host", "port", "service", "open", "closed", "filtered",
        ],
        "core-concepts": [
            "-sV", "-p-", "-O", "-sC", "SYN",
        ],
        "hands-on-practice": [
            "enumeration mindset", "-Pn", "IDS", "Vulnerability research",
        ],
    }

    # Claims this module must never quietly lose — the exact WRONG/
    # CORRECT corrections the driving spec named explicitly.
    _REQUIRED_CORRECTIONS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "Closed means the host responded but no service is listening",
            "Filtered means Nmap cannot determine whether the port is open",
        ],
        "core-concepts": [
            ("Port 80 is conventionally associated with HTTP, but service "
             "detection provides stronger evidence"),
            "Nmap primarily provides discovery and enumeration capabilities",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(f"roadmap/intermediate/nmap/{slug}.md")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
            assert len(html) > 3000, f"{slug}: suspiciously short ({len(html)} chars)"

    def test_lessons_contain_their_taught_terms(self, app):
        for slug, terms in self._EXPECTED_TERMS.items():
            html = self._render(app, slug)
            for term in terms:
                assert term in html, f"{slug}: missing expected term {term!r}"

    def test_lessons_keep_their_misconception_corrections(self, app):
        """The exact WRONG/CORRECT corrections the driving spec required:
        closed != offline, filtered != closed, port 80 != proof of HTTP,
        Nmap != automatic vulnerability scanner. Losing any of these
        would make the module technically wrong, not merely thinner."""
        for slug, claims in self._REQUIRED_CORRECTIONS.items():
            html = self._render(app, slug)
            for claim in claims:
                assert claim in html, f"{slug}: lost required correction {claim!r}"

    def test_lessons_contain_real_code_examples(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert "<pre>" in html and "<code>" in html, f"{slug}: no code block rendered"

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_no_exploitation_or_evasion_framing(self, app):
        """Permanent safety rule: this module teaches reconnaissance and
        enumeration, never exploitation or detection evasion. Guards
        against the module ever drifting into content this ticket was
        explicitly told not to write."""
        banned = ("exploit the", "bypass authorization", "evade detection",
                  "avoid being detected", "hide from the firewall")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains unsafe framing {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="nmap").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2,
        and the module still sits at Intermediate display_order 1."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="nmap").first()
            assert module.id == 9
            assert module.display_order == 1
            assert module.xp_reward == 175
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [l.id for l in lessons] == [25, 26, 27]
            assert [l.slug for l in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [l.display_order for l in lessons] == [1, 2, 3]
            assert [l.xp_reward for l in lessons] == [25, 50, 100]
            assert [l.estimated_minutes for l in lessons] == [10, 20, 30]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_practice_links_scoped_to_hands_on_only_and_no_terminal_link(self, app, student):
        """Only hands-on-practice links out, to both the real lab and
        the real mission. No lesson offers the free-practice terminal:
        the bare sandbox has no simulated network, so `nmap` would fail
        there with 'no network configured for this session'."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, expect_link in (
                ("introduction", False),
                ("core-concepts", False),
                ("hands-on-practice", True),
            ):
                ctx = get_lesson_view_context(student_user, "nmap", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert not practice.get("show_terminal")
                assert bool(practice.get("lab_slug")) is expect_link
                assert bool(practice.get("mission_slug")) is expect_link
                if expect_link:
                    assert practice["lab_slug"] == "nmap-basics"
                    assert practice["mission_slug"] == "nmap-fundamentals"

    def test_lab_link_points_to_a_real_route_and_a_real_lab(self, app):
        with app.test_request_context():
            from flask import url_for
            assert url_for("labs.detail", slug="nmap-basics") == "/labs/nmap-basics"
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug="nmap-basics").first()
            assert lab is not None and lab.is_active and lab.is_interactive
            assert lab.title == "Nmap: Your First Scan"

    def test_mission_link_points_to_a_real_route_and_a_real_mission(self, app):
        from app.core.missions.mission_loader import MISSIONS

        with app.test_request_context():
            from flask import url_for
            assert url_for("terminal.mission_page", slug="nmap-fundamentals") == (
                "/terminal/mission/nmap-fundamentals"
            )
        assert "nmap-fundamentals" in MISSIONS
        assert MISSIONS["nmap-fundamentals"]["title"] == "Nmap Fundamentals"

    def test_quoted_scan_output_matches_the_real_simulator(self, app):
        """Every scan quoted in all three lessons was captured by
        actually running the real `_nmap()` terminal command handler
        against the real Nmap Fundamentals mission network. If the
        simulator's network topology or output formatting ever
        changes, the lessons become fabricated output — fail here
        rather than ship a lie."""
        from app.core.missions.mission_loader import MISSIONS
        from app.core.terminal.commands import _nmap
        from app.core.terminal.network import build_network

        class _FakeShell:
            pass

        net = build_network(MISSIONS["nmap-fundamentals"]["network"])

        def scan(args):
            sh = _FakeShell()
            sh.network = net
            return _nmap(sh, args)

        checks = {
            "introduction": [
                ["-sn", "10.10.10.0/24"],
            ],
            "core-concepts": [
                ["10.10.10.10"],
                ["-p", "20-30", "10.10.10.30"],
                ["-sV", "10.10.10.10"],
                ["-sT", "10.10.10.10"],
                ["-sU", "10.10.10.53"],
                ["10.10.10.40"],
                ["-Pn", "-O", "10.10.10.40"],
            ],
            "hands-on-practice": [
                ["-sn", "10.10.10.0/24"],
                ["10.10.10.10"],
                ["-p", "22", "10.10.10.30"],
                ["-p", "20-30", "10.10.10.30"],
                ["-sV", "10.10.10.10"],
                ["-sV", "10.10.10.30"],
                ["10.10.10.40"],
                ["-Pn", "-O", "-sV", "10.10.10.40"],
            ],
        }
        for slug, commands in checks.items():
            raw = self._raw_lesson(slug)
            for args in commands:
                output = scan(args)
                for line in output.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    assert line in raw, (
                        f"{slug}: quoted output no longer matches real "
                        f"simulator for `nmap {' '.join(args)}` — {line!r}"
                    )

    @staticmethod
    def _raw_lesson(slug):
        from pathlib import Path

        import app as app_pkg
        path = (Path(app_pkg.__file__).parent / "content" / "roadmap"
                / "intermediate" / "nmap" / f"{slug}.md")
        return path.read_text(encoding="utf-8")

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        """introduction is a preview and always reachable; core-concepts
        and hands-on-practice require the module unlocked (this is
        Intermediate's first module, unlocked in parallel with Beginner
        for a new user)."""
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="nmap").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/nmap/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body
            r = c.get("/roadmap/nmap/hands-on-practice/")
            body = r.data.decode("utf-8")
            assert "Nmap: Your First Scan" in body
            assert "Nmap Fundamentals" in body
            # No terminal free-practice CTA anywhere in this module.
            r = c.get("/roadmap/nmap/introduction/")
            body = r.data.decode("utf-8")
            assert "Try it in the Terminal" not in body

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, uid = student
        with app.app_context():
            from app.extensions import db
            from app.roadmap.models import RoadmapModule, UserModuleProgress
            module = RoadmapModule.query.filter_by(slug="nmap").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/nmap/core-concepts/")
            body = r.data.decode("utf-8")
            assert 'data-mentor-lab="Nmap' in body
            assert "Core Concepts" in body

    def test_completion_awards_xp_exactly_once(self, app, student):
        """Completing an Nmap lesson awards its XP once; a repeat POST
        (the refresh case) must not award it again."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="nmap").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()
            before = User.query.get(uid).xp

        with app.test_client() as c:
            _login(c, uname)
            c.post("/roadmap/nmap/core-concepts/complete", follow_redirects=True)
            with app.app_context():
                after_first = User.query.get(uid).xp
            c.post("/roadmap/nmap/core-concepts/complete", follow_redirects=True)
            with app.app_context():
                after_second = User.query.get(uid).xp

        assert after_first == before + 50, "core-concepts should award exactly 50 XP"
        assert after_second == after_first, "XP awarded twice for one lesson"

    def test_module_completion_awards_bonus(self, app, student):
        """Completing all three Nmap lessons completes the module and
        awards its 175 XP bonus exactly once. Asserts a *delta*, not an
        absolute total: `student` is module-scoped and shared with
        every other class in this file, including
        TestCompletionAwardsXpExactlyOnce above (which already
        completed `nmap/core-concepts` for this same user) — so
        completing it again here is correctly a no-op XP-wise, and the
        user's XP already carries whatever every earlier class in this
        file awarded it for other modules."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import (
            Lesson,
            RoadmapModule,
            UserLessonProgress,
            UserModuleProgress,
        )

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="nmap").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()
            before = User.query.get(uid).xp
            lessons_already_done = {
                lesson.slug for lesson in
                Lesson.query.filter_by(module_id=module.id).join(
                    UserLessonProgress,
                    (UserLessonProgress.lesson_id == Lesson.id)
                    & (UserLessonProgress.user_id == uid)
                    & (UserLessonProgress.completed.is_(True)),
                ).all()
            }

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                c.post(f"/roadmap/nmap/{slug}/complete", follow_redirects=True)

        xp_by_slug = {"introduction": 25, "core-concepts": 50, "hands-on-practice": 100}
        expected_lesson_xp = sum(
            xp for slug, xp in xp_by_slug.items() if slug not in lessons_already_done
        )

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="nmap").first()
            row = UserModuleProgress.query.filter_by(user_id=uid, module_id=module.id).first()
            assert row.completed is True
            assert row.bonus_awarded is True
            after = User.query.get(uid).xp
            assert after == before + expected_lesson_xp + 175


class TestWiresharkContent:
    """Guards the real content written for YC-037.2 — Wireshark, module 2
    of Intermediate. Pins that each lesson teaches its actual material,
    that every quoted capture/filter/follow output is byte-for-byte what
    this platform's real packet-analysis simulator
    (`app/core/terminal/packets.py` driven through the real
    `capture`/`packets`/`show`/`follow`/`filter` command handlers in
    `app/core/terminal/commands.py`) actually produces, and that the
    module's lab (`wireshark-basics`) and mission
    (`wireshark-fundamentals`) links are real routes scoped to
    `hands-on-practice` only."""

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "frame", "segment", "encapsulation", "MAC address",
            "endpoint", "packet list",
        ],
        "core-concepts": [
            "SYN", "SYN, ACK", "FIN", "RST", "PSH",
            "three-way handshake", "retransmission",
            "display filter", "capture filter", "TLS",
            "ip.addr", "tcp.port", "Follow TCP Stream",
        ],
        "hands-on-practice": [
            "investigation", "baseline", "OBSERVATION",
            "INTERPRETATION", "CONCLUSION", "CONFIDENCE",
            "authorization", "Wireshark Fundamentals",
        ],
    }

    # Claims this module must never quietly lose — the exact WRONG/
    # CORRECT corrections the driving spec named explicitly. Losing any
    # of these makes the module technically wrong, not merely thinner.
    _REQUIRED_CORRECTIONS: ClassVar[dict[str, list[str]]] = {
        "core-concepts": [
            "Retransmissions mean an attack",
            ("Retransmissions usually reflect ordinary network behaviour "
             "— loss, congestion, or timing"),
            "A RST means an attacker reset the connection",
            "A display filter changes what was captured",
            ("A display filter changes what is currently shown from an "
             "existing capture"),
            "It's HTTPS, so Wireshark shows nothing",
            ("Encryption protects the application payload. A substantial "
             "amount of metadata remains fully visible"),
            "Wireshark says it's HTTP, so it's HTTP",
            "A PSH flag proves an application event happened",
        ],
        "introduction": [
            "Destination port 80, so this is HTTP",
        ],
    }

    def _render(self, app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(
                f"roadmap/intermediate/wireshark/{slug}.md"
            )

    @staticmethod
    def _raw_lesson(slug):
        from pathlib import Path

        import app as app_pkg
        path = (Path(app_pkg.__file__).parent / "content" / "roadmap"
                / "intermediate" / "wireshark" / f"{slug}.md")
        return path.read_text(encoding="utf-8")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
            assert len(html) > 3000, f"{slug}: suspiciously short ({len(html)} chars)"

    def test_lessons_contain_their_taught_terms(self, app):
        for slug, terms in self._EXPECTED_TERMS.items():
            html = self._render(app, slug)
            for term in terms:
                assert term in html, f"{slug}: missing expected term {term!r}"

    def test_lessons_keep_their_misconception_corrections(self, app):
        for slug, claims in self._REQUIRED_CORRECTIONS.items():
            html = self._render(app, slug)
            for claim in claims:
                assert claim in html, f"{slug}: lost required correction {claim!r}"

    def test_lessons_contain_real_code_examples(self, app):
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug)
            assert "<pre>" in html and "<code>" in html, f"{slug}: no code block rendered"

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_no_unauthorized_capture_or_credential_framing(self, app):
        """Permanent safety rule: this module teaches authorized,
        defensive packet analysis. It must never drift into teaching
        interception of third-party traffic, credential harvesting,
        session hijacking, or monitoring evasion."""
        banned = ("harvest credentials", "steal the session",
                  "hijack the session", "capture your neighbour",
                  "evade detection", "avoid being detected",
                  "bypass encryption", "decrypt any https")
        for slug in ("introduction", "core-concepts", "hands-on-practice"):
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains unsafe framing {phrase!r}"

    def test_authorization_boundary_is_stated(self, app):
        """Every lesson touching capture must state the boundary; the
        hands-on lesson must state it explicitly and up front."""
        intro = self._render(app, "introduction")
        assert "authorization boundary" in intro.lower()
        hands = self._render(app, "hands-on-practice")
        assert "Authorization Comes First" in hands
        for phrase in ("interception", "does not teach"):
            assert phrase in hands.lower(), f"hands-on-practice: missing {phrase!r}"

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="wireshark").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2,
        and the module still sits at Intermediate display_order 2."""
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="wireshark").first()
            assert module.id == 10
            assert module.display_order == 2
            assert module.xp_reward == 175
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [lesson.id for lesson in lessons] == [28, 29, 30]
            assert [lesson.slug for lesson in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [lesson.display_order for lesson in lessons] == [1, 2, 3]
            assert [lesson.xp_reward for lesson in lessons] == [25, 50, 100]
            assert [lesson.estimated_minutes for lesson in lessons] == [10, 20, 30]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_practice_links_scoped_to_hands_on_only_and_no_terminal_link(self, app, student):
        """Only hands-on-practice links out, to both the real lab and
        the real mission. No lesson offers the free-practice terminal:
        `start_shell()` never attaches a PacketLab, so every command
        this module teaches fails there with 'no packet lab configured
        for this session'."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, expect_link in (
                ("introduction", False),
                ("core-concepts", False),
                ("hands-on-practice", True),
            ):
                ctx = get_lesson_view_context(student_user, "wireshark", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert not practice.get("show_terminal")
                assert bool(practice.get("lab_slug")) is expect_link
                assert bool(practice.get("mission_slug")) is expect_link
                if expect_link:
                    assert practice["lab_slug"] == "wireshark-basics"
                    assert practice["mission_slug"] == "wireshark-fundamentals"

    def test_free_practice_terminal_really_has_no_packet_lab(self, app):
        """The reason `wireshark` is excluded from
        _TERMINAL_PRACTICE_MODULES, asserted rather than assumed — if
        the bare sandbox ever gains a PacketLab, this fails and the
        exclusion should be revisited."""
        from app.core.terminal.shell import Shell

        sh = Shell()
        assert sh.packet_lab is None
        assert sh.execute("capture handshake") == (
            "capture: no packet lab configured for this session"
        )

    def test_lab_link_points_to_a_real_route_and_a_real_lab(self, app):
        with app.test_request_context():
            from flask import url_for
            assert url_for("labs.detail", slug="wireshark-basics") == (
                "/labs/wireshark-basics"
            )
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug="wireshark-basics").first()
            assert lab is not None and lab.is_active and lab.is_interactive
            assert lab.title == "Wireshark: Capture & Inspect"

    def test_mission_link_points_to_a_real_route_and_a_real_mission(self, app):
        from app.core.missions.mission_loader import MISSIONS

        with app.test_request_context():
            from flask import url_for
            assert url_for("terminal.mission_page", slug="wireshark-fundamentals") == (
                "/terminal/mission/wireshark-fundamentals"
            )
        assert "wireshark-fundamentals" in MISSIONS
        assert MISSIONS["wireshark-fundamentals"]["title"] == "Wireshark Fundamentals"

    def test_further_labs_named_in_lesson_text_are_real(self, app):
        """hands-on-practice names two further labs as next steps rather
        than linking them. Named-but-unlinked is still a claim about
        reality, so it gets verified too."""
        raw = self._raw_lesson("hands-on-practice")
        with app.app_context():
            from app.labs.models import Lab
            for slug, title in (
                ("wireshark-protocols", "Wireshark: Protocol Analysis"),
                ("wireshark-advanced", "Wireshark: Advanced Analysis"),
            ):
                lab = Lab.query.filter_by(slug=slug).first()
                assert lab is not None and lab.is_active, f"{slug}: not a real lab"
                assert lab.title == title
                assert title in raw, f"{title!r} named in lesson but lab check drifted"

    # ── Real-evidence guard ────────────────────────────────────────────
    # Every command sequence whose FULL output a lesson quotes verbatim.
    # Each entry is (capture_to_open_first, [commands...]); the capture
    # name is None for the bare `capture` listing.
    _FULL_OUTPUT_CHECKS: ClassVar[dict[str, list[tuple]]] = {
        "introduction": [
            ("handshake", ["capture handshake", "packets", "show 1"]),
        ],
        "core-concepts": [
            ("handshake", ["capture handshake", "packets",
                           "show 1", "show 2", "show 3"]),
            ("http", ["capture http", "packets", "show 4", "show 6",
                      "filter tcp", "filter tcp.port == 80", "follow 4"]),
            ("dns", ["capture dns", "packets", "show 1", "show 2",
                     "filter udp", "filter udp.port == 53"]),
            ("mixed", ["capture mixed", "filter dns",
                       "filter ip.addr == 10.10.10.99"]),
        ],
        "hands-on-practice": [
            (None, ["capture"]),
            ("icmp", ["capture icmp", "packets", "show 1"]),
            ("handshake", ["capture handshake", "packets"]),
            ("dns", ["capture dns", "packets"]),
            ("http", ["capture http", "filter http", "follow 4"]),
            ("mixed", ["capture mixed", "filter http",
                       "filter tcp.port == 80"]),
            ("investigation", ["capture investigation", "filter http",
                               "filter ip.addr == 10.10.10.77",
                               "show 42", "show 45", "follow 42"]),
        ],
    }

    # Sequences a lesson quotes only PARTIALLY (the full listing would be
    # unreadable). Checked as a line-slice of the real output so the
    # quoted excerpt still can't drift from the simulator.
    _PARTIAL_OUTPUT_CHECKS: ClassVar[list[tuple]] = [
        # hands-on §9 quotes the header plus the first 9 rows of the
        # 32-packet `mixed` listing, then says the listing continues.
        ("hands-on-practice", "mixed", "packets", 0, 10),
        # hands-on §10 step 3 quotes rows 26-29 of the 45-packet
        # `investigation` listing (the incomplete-connection detour).
        ("hands-on-practice", "investigation", "packets", 26, 30),
    ]

    @staticmethod
    def _shell():
        from app.core.terminal.packets import CAPTURE_REGISTRY, build_packet_lab
        from app.core.terminal.shell import Shell

        sh = Shell()
        sh.packet_lab = build_packet_lab(list(CAPTURE_REGISTRY.keys()))
        return sh

    def test_quoted_capture_output_matches_the_real_simulator(self, app):
        """Every capture, packet listing, packet detail, filter result
        and followed conversation quoted in all three lessons was
        captured by actually running the real terminal command handlers
        against the real PacketLab the Wireshark Fundamentals mission
        loads. If the simulator's datasets or output formatting ever
        change, the lessons become fabricated output — fail here rather
        than ship a lie."""
        for slug, groups in self._FULL_OUTPUT_CHECKS.items():
            raw = self._raw_lesson(slug)
            for capture_name, commands in groups:
                sh = self._shell()
                if capture_name is not None:
                    sh.execute(f"capture {capture_name}")
                for command in commands:
                    output = sh.execute(command)
                    for line in output.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        assert line in raw, (
                            f"{slug}: quoted output no longer matches the real "
                            f"simulator for `{command}` on capture "
                            f"{capture_name!r} — {line!r}"
                        )

    def test_partially_quoted_output_matches_the_real_simulator(self, app):
        for slug, capture_name, command, start, stop in self._PARTIAL_OUTPUT_CHECKS:
            raw = self._raw_lesson(slug)
            sh = self._shell()
            sh.execute(f"capture {capture_name}")
            lines = sh.execute(command).splitlines()[start:stop]
            assert lines, f"{slug}: partial slice for `{command}` is empty"
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                assert line in raw, (
                    f"{slug}: partially quoted output drifted from the real "
                    f"simulator for `{command}` on {capture_name!r} — {line!r}"
                )

    def test_capture_packet_counts_claimed_in_lessons_are_real(self, app):
        """hands-on §3 tabulates each capture's packet count, and the
        lessons state counts in prose. Pinned against the real
        datasets."""
        from app.core.terminal.packets import CAPTURE_REGISTRY, build_packet_lab

        lab = build_packet_lab(list(CAPTURE_REGISTRY.keys()))
        expected = {"handshake": 3, "dns": 2, "http": 8, "icmp": 2,
                    "mixed": 32, "investigation": 45}
        actual = {name: len(cap.packets) for name, cap in lab.captures.items()}
        assert actual == expected

    def test_flags_taught_as_absent_really_are_absent(self, app):
        """Core Concepts §4/§7/§8 state plainly that no RST and no
        retransmission exists in this platform's captures, and teach
        both concepts without quoting output for exactly that reason.
        If a capture ever gains a RST, that honesty claim becomes false
        and the lessons should quote the real thing instead."""
        from app.core.terminal.packets import CAPTURE_REGISTRY, build_packet_lab

        lab = build_packet_lab(list(CAPTURE_REGISTRY.keys()))
        flags = {p.tcp_flags for cap in lab.captures.values()
                 for p in cap.packets if p.tcp_flags}
        assert flags == {"SYN", "SYN, ACK", "ACK", "FIN, ACK", "PSH, ACK"}
        assert not any("RST" in f for f in flags)

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="wireshark").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/wireshark/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body
            r = c.get("/roadmap/wireshark/hands-on-practice/")
            body = r.data.decode("utf-8")
            assert "Wireshark: Capture &amp; Inspect" in body
            assert "Wireshark Fundamentals" in body
            assert "/labs/wireshark-basics" in body
            assert "/terminal/mission/wireshark-fundamentals" in body
            # No terminal free-practice CTA anywhere in this module.
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                r = c.get(f"/roadmap/wireshark/{slug}/")
                assert "Try it in the Terminal" not in r.data.decode("utf-8")

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, uid = student
        with app.app_context():
            from app.extensions import db
            from app.roadmap.models import RoadmapModule, UserModuleProgress
            module = RoadmapModule.query.filter_by(slug="wireshark").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/roadmap/wireshark/core-concepts/")
            body = r.data.decode("utf-8")
            assert 'data-mentor-lab="Wireshark' in body
            assert "Core Concepts" in body

    def test_completion_awards_xp_exactly_once(self, app, student):
        """Completing a Wireshark lesson awards its XP once; a repeat
        POST (the refresh case) must not award it again."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="wireshark").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()
            before = User.query.get(uid).xp

        with app.test_client() as c:
            _login(c, uname)
            c.post("/roadmap/wireshark/core-concepts/complete", follow_redirects=True)
            with app.app_context():
                after_first = User.query.get(uid).xp
            c.post("/roadmap/wireshark/core-concepts/complete", follow_redirects=True)
            with app.app_context():
                after_second = User.query.get(uid).xp

        assert after_first == before + 50, "core-concepts should award exactly 50 XP"
        assert after_second == after_first, "XP awarded twice for one lesson"

    def test_module_completion_awards_bonus(self, app, student):
        """Completing all three Wireshark lessons completes the module
        and awards its 175 XP bonus exactly once. Asserts a *delta*, not
        an absolute total — `student` is module-scoped and shared with
        every other class in this file, including
        test_completion_awards_xp_exactly_once above."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import (
            Lesson,
            RoadmapModule,
            UserLessonProgress,
            UserModuleProgress,
        )

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="wireshark").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()
            before = User.query.get(uid).xp
            lessons_already_done = {
                lesson.slug for lesson in
                Lesson.query.filter_by(module_id=module.id).join(
                    UserLessonProgress,
                    (UserLessonProgress.lesson_id == Lesson.id)
                    & (UserLessonProgress.user_id == uid)
                    & (UserLessonProgress.completed.is_(True)),
                ).all()
            }

        with app.test_client() as c:
            _login(c, uname)
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                c.post(f"/roadmap/wireshark/{slug}/complete", follow_redirects=True)

        xp_by_slug = {"introduction": 25, "core-concepts": 50, "hands-on-practice": 100}
        expected_lesson_xp = sum(
            xp for slug, xp in xp_by_slug.items() if slug not in lessons_already_done
        )

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="wireshark").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            assert row.completed is True
            assert row.bonus_awarded is True
            after = User.query.get(uid).xp
            assert after == before + expected_lesson_xp + 175


class TestBurpSuiteContent:
    """Guards the real content written for YC-037.3 — Burp Suite, module 3
    of Intermediate. Pins that each lesson teaches its actual material,
    that every quoted request/response/history/compare block is
    byte-for-byte what this platform's real proxy simulator
    (`app/core/terminal/web.py` driven through the real `proxy`/
    `intercept`/`open`/`forward`/`drop`/`edit`/`requests`/`repeater`/
    `compare` command handlers in `app/core/terminal/commands.py`)
    actually produces, and that the module's mission
    (`burp-fundamentals`, on core-concepts and hands-on-practice) and lab
    (`websec-http`, on hands-on-practice) links are real, reachable
    routes."""

    _SLUGS: ClassVar[tuple[str, ...]] = (
        "introduction", "core-concepts", "hands-on-practice",
    )

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "intercepting proxy", "HTTP history", "authorization boundary",
            "request line", "status line", "blank line",
            "User-Agent", "Content-Length", "Scope", "forward", "drop",
        ],
        "core-concepts": [
            "Repeater", "one variable", "query string", "path segment",
            "form body", "JSON body", "Header value", "Cookie value",
            "Set-Cookie", "session cookie", "Authorization: Bearer",
            "bearer token", "authentication", "authorization",
            "401", "403", "404", "302",
            "OBSERVATION", "INTERPRETATION", "CONCLUSION",
        ],
        "hands-on-practice": [
            "Authorization Comes First", "Burp Suite Fundamentals",
            "OBSERVATION", "INTERPRETATION", "CONCLUSION", "CONFIDENCE",
            "baseline", "Evidence Report", "Repeater",
        ],
    }

    # The exact WRONG/CORRECT corrections the driving spec named. Losing
    # any of these makes the module technically wrong, not merely thinner.
    _REQUIRED_CORRECTIONS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "Burp is a vulnerability scanner.",
            "Burp is primarily a toolkit for",
            "Burp just sees inside HTTPS automatically.",
            "HTTPS traffic is encrypted between client and server.",
        ],
        "core-concepts": [
            "I changed a parameter and the response changed, so it's vulnerable.",
            "Changing an input is a <em>test</em>",
            "Repeater exploits the server.",
            "Repeater gives you controlled replay and modification",
            "401 means you don't have permission.",
            "generally indicates <em>missing or invalid authentication</em>",
            "The button isn't shown to this user, so this user can't do it.",
            "The server must enforce authorization regardless of what the interface displays.",
            "Cookie = authentication.",
            "A cookie is a general mechanism for carrying state",
        ],
    }

    # Every command sequence a lesson quotes, replayed against the real
    # simulator. Each entry is (command, lesson-slug-or-None, slice-or-None):
    # None as the slug means "setup step, not quoted"; a slice means the
    # lesson quotes only those output lines.
    _LOGIN_STUDENT: ClassVar[str] = (
        'open -X POST -d "username=student&password=training123" '
        "https://cybershop.training/auth/login"
    )
    _LOGIN_ADMIN: ClassVar[str] = (
        'open -X POST -d "username=admin&password=admin123" '
        "https://cybershop.training/auth/login"
    )
    _POST_WRONG_KEY: ClassVar[str] = (
        'open -X POST -H "Content-Type: application/json" '
        "-d '{\"Display_Name\": \"Alex Rivera\"}' "
        "https://cybershop.training/api/profile"
    )
    _POST_RIGHT_KEY: ClassVar[str] = (
        'open -X POST -H "Content-Type: application/json" '
        "-d '{\"display_name\": \"Alex Rivera\"}' "
        "https://cybershop.training/api/profile"
    )

    @staticmethod
    def _render(app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(
                f"roadmap/intermediate/burp-suite/{slug}.md"
            )

    @staticmethod
    def _raw_lesson(slug):
        from pathlib import Path

        import app as app_pkg
        path = (Path(app_pkg.__file__).parent / "content" / "roadmap"
                / "intermediate" / "burp-suite" / f"{slug}.md")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _shell():
        """A shell with the same simulated web environment the real
        Burp Suite Fundamentals mission attaches (its `web_lab` key is
        "profile-mismatch", see app/core/missions/mission_loader.py)."""
        from app.core.terminal.shell import Shell
        from app.core.terminal.web import build_web_lab

        sh = Shell()
        sh.web_lab = build_web_lab("profile-mismatch")
        return sh

    def test_all_three_lessons_render_real_content(self, app):
        for slug in self._SLUGS:
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
            assert len(html) > 3000, f"{slug}: suspiciously short ({len(html)} chars)"

    def test_lessons_contain_their_taught_terms(self, app):
        for slug, terms in self._EXPECTED_TERMS.items():
            html = self._render(app, slug)
            for term in terms:
                assert term in html, f"{slug}: missing expected term {term!r}"

    def test_lessons_keep_their_misconception_corrections(self, app):
        for slug, claims in self._REQUIRED_CORRECTIONS.items():
            html = self._render(app, slug)
            for claim in claims:
                assert claim in html, f"{slug}: lost required correction {claim!r}"

    def test_lessons_contain_real_code_examples(self, app):
        for slug in self._SLUGS:
            html = self._render(app, slug)
            assert "<pre>" in html and "<code>" in html, f"{slug}: no code block rendered"

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder")
        for slug in self._SLUGS:
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    def test_no_unauthorized_or_offensive_framing(self, app):
        """Permanent safety rule: this module teaches authorized,
        evidence-driven web testing. It must never drift into teaching
        interception of third-party traffic, session/cookie theft,
        credential attacks, or testing of live systems."""
        banned = ("steal the session", "steal a session", "hijack the session",
                  "steal the cookie", "forge a session", "forge the cookie",
                  "intercept your neighbour", "evade detection",
                  "avoid being detected", "bypass authentication",
                  "any public website", "any live site")
        for slug in self._SLUGS:
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains unsafe framing {phrase!r}"

    def test_authorization_boundary_is_stated(self, app):
        """Every lesson must carry the boundary; introduction states it
        before any technique and hands-on states it up front."""
        intro = self._render(app, "introduction")
        assert "The Authorization Boundary" in intro
        assert "explicit written permission" in intro
        hands = self._render(app, "hands-on-practice")
        assert "Authorization Comes First" in hands
        core = self._render(app, "core-concepts")
        for html, slug in ((intro, "introduction"), (core, "core-concepts"),
                           (hands, "hands-on-practice")):
            assert "authoriz" in html.lower(), f"{slug}: no authorization framing"

    def test_server_is_the_security_boundary_is_taught(self, app):
        """The single claim this module exists to install."""
        core = self._render(app, "core-concepts")
        assert "The browser is not the security boundary. The server is." in core
        hands = self._render(app, "hands-on-practice")
        assert "The server is the security boundary." in hands

    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="burp-suite").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2,
        and the module still sits at Intermediate display_order 3."""
        from app.roadmap.models import Lesson, RoadmapCategory, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="burp-suite").first()
            assert module.id == 11
            assert module.display_order == 3
            # Resolved by title, not by a hardcoded id: this file shares one
            # physical sqlite database with every other test module in a
            # pytest run, and an unrelated module may create a category
            # first, shifting `RoadmapCategory.id`. The module/lesson
            # primary keys above are stable because `_insert_curriculum()`
            # always inserts them in the same order.
            intermediate = RoadmapCategory.query.filter_by(
                title="Intermediate").first()
            assert module.category_id == intermediate.id
            assert module.difficulty == "intermediate"
            assert module.estimated_hours == 1
            assert module.xp_reward == 175
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [lesson.id for lesson in lessons] == [31, 32, 33]
            assert [lesson.slug for lesson in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [lesson.display_order for lesson in lessons] == [1, 2, 3]
            assert [lesson.xp_reward for lesson in lessons] == [25, 50, 100]
            assert [lesson.estimated_minutes for lesson in lessons] == [10, 20, 30]
            assert [lesson.content_path for lesson in lessons] == [
                "roadmap/intermediate/burp-suite/introduction.md",
                "roadmap/intermediate/burp-suite/core-concepts.md",
                "roadmap/intermediate/burp-suite/hands-on-practice.md",
            ]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_intermediate_module_order_unchanged(self, app):
        """Nmap < Wireshark < Burp Suite, still 1/2/3."""
        from app.roadmap.models import RoadmapCategory, RoadmapModule

        with app.app_context():
            intermediate = RoadmapCategory.query.filter_by(
                title="Intermediate").first()
            order = [
                (m.slug, m.display_order) for m in
                RoadmapModule.query.filter_by(category_id=intermediate.id)
                .order_by(RoadmapModule.display_order).limit(4).all()
            ]
            assert order == [("nmap", 1), ("wireshark", 2),
                             ("burp-suite", 3), ("owasp-top-10", 4)]

    def test_practice_links_are_scoped_and_no_terminal_link(self, app, student):
        """introduction has no practice CTA (its exercises are reasoning
        questions about output already printed in the lesson);
        core-concepts links the mission only (its §14 Repeater experiment
        is command-driven); hands-on-practice links both the mission and
        the lab. No lesson offers the free-practice terminal."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        expected = {
            "introduction": (False, False),
            "core-concepts": (True, False),
            "hands-on-practice": (True, True),
        }
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, (want_mission, want_lab) in expected.items():
                ctx = get_lesson_view_context(student_user, "burp-suite", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert not practice.get("show_terminal")
                assert bool(practice.get("mission_slug")) is want_mission, slug
                assert bool(practice.get("lab_slug")) is want_lab, slug
                if want_mission:
                    assert practice["mission_slug"] == "burp-fundamentals"
                    assert practice["mission_title"] == "Burp Suite Fundamentals"
                if want_lab:
                    assert practice["lab_slug"] == "websec-http"
                    assert practice["lab_title"] == "HTTP Requests & Responses"

    def test_free_practice_terminal_really_has_no_web_lab(self, app):
        """The reason `burp-suite` is excluded from
        _TERMINAL_PRACTICE_MODULES, asserted rather than assumed."""
        from app.core.terminal.shell import Shell

        sh = Shell()
        assert sh.web_lab is None
        assert sh.execute("proxy") == (
            "proxy: no simulated web environment configured for this session"
        )
        assert sh.execute("open https://cybershop.training/products") == (
            "open: no simulated web environment configured for this session"
        )

    def test_lab_link_points_to_a_real_reachable_lab(self, app):
        """`websec-http` is real, active, interactive AND has no
        prerequisite — the reason it is the one websec lab this module
        can link without producing a dead CTA (`labs.detail` redirects a
        locked lab back to the catalogue)."""
        with app.test_request_context():
            from flask import url_for
            assert url_for("labs.detail", slug="websec-http") == "/labs/websec-http"
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug="websec-http").first()
            assert lab is not None and lab.is_active and lab.is_interactive
            assert lab.title == "HTTP Requests & Responses"
            assert lab.prerequisite_lab_id is None

    def test_other_websec_labs_named_in_lesson_are_real_but_gated(self, app):
        """hands-on §13 names the remaining websec labs as belonging to a
        later module and explains they unlock in sequence. Named-but-
        unlinked is still a claim about reality, so both halves of it get
        verified: the labs exist, and they really are prerequisite-gated."""
        raw = self._raw_lesson("hands-on-practice")
        with app.app_context():
            from app.labs.models import Lab
            for slug in ("websec-idor", "websec-auth", "websec-sessions",
                         "websec-headers"):
                lab = Lab.query.filter_by(slug=slug).first()
                assert lab is not None and lab.is_active, f"{slug}: not a real lab"
                assert lab.prerequisite_lab_id is not None, (
                    f"{slug}: lesson says it is gated, but it isn't"
                )
                assert slug in raw, f"{slug}: named in lesson but check drifted"

    def test_mission_link_points_to_a_real_route_and_a_real_mission(self, app):
        from app.core.missions.mission_loader import MISSIONS

        with app.test_request_context():
            from flask import url_for
            assert url_for("terminal.mission_page", slug="burp-fundamentals") == (
                "/terminal/mission/burp-fundamentals"
            )
        assert "burp-fundamentals" in MISSIONS
        mission = MISSIONS["burp-fundamentals"]
        assert mission["title"] == "Burp Suite Fundamentals"
        # hands-on §13 states the mission has fourteen scored objectives.
        assert len(mission["objectives"]) == 14
        # The lessons' quoted output is captured from this scenario.
        assert mission["web_lab"] == "profile-mismatch"

    def test_training_credentials_named_in_lessons_are_the_real_ones(self, app):
        """Every credential/token printed in these lessons is a fixed,
        fictional training constant defined in the simulator. Pinned so a
        lesson can never quote a value the environment doesn't accept."""
        from app.core.terminal.web import _USERS, API_TOKEN, HOST

        assert HOST == "cybershop.training"
        assert _USERS["student"] == "training123"
        assert _USERS["admin"] == "admin123"
        assert _USERS["analyst"] == "analyst123"
        assert API_TOKEN == "training-token-001"
        for slug in self._SLUGS:
            raw = self._raw_lesson(slug)
            assert "cybershop.training" in raw
        hands = self._raw_lesson("hands-on-practice")
        for value in ("student", "training123", "admin", "admin123",
                      "analyst", "analyst123"):
            assert value in hands, f"hands-on-practice: {value!r} not named"
        assert API_TOKEN in self._raw_lesson("core-concepts")

    # ── Real-evidence guard ────────────────────────────────────────────
    def _sessions(self):
        """Each session is an ordered command list replayed on one shell,
        mirroring exactly how the lessons present them. Entries are
        (command, lesson-slug-or-None, slice-or-None): None as the slug
        marks a setup step the lesson doesn't quote; a slice marks output
        the lesson quotes only partially."""
        return {
            # Introduction §5-§11.
            "intro": [
                ("proxy", "introduction", None),
                ("open https://cybershop.training/products?id=42",
                 "introduction", None),
                ("intercept on", "introduction", None),
                ("open https://cybershop.training/products?id=42",
                 "introduction", None),
                ("forward", "introduction", None),
                ("open https://cybershop.training/products?id=42",
                 "introduction", None),
                ("drop", "introduction", None),
                ("intercept off", None, None),
                # §7 quotes the request half of the login exchange only.
                (self._LOGIN_STUDENT, "introduction", (0, 9)),
                ("open https://evil.example.com/", "introduction", None),
            ],
            # Core Concepts §3-§13, one continuous session so the history
            # numbers in the quoted `compare`/`requests` output are real.
            "core": [
                ("proxy", "core-concepts", None),
                ("open https://cybershop.training/products?id=42", None, None),
                ("repeater 1", "core-concepts", None),
                ("edit query id 43", "core-concepts", None),
                ("repeater send", "core-concepts", None),
                ("compare 1 2", "core-concepts", None),
                ("open https://cybershop.training/account", "core-concepts", None),
                (self._LOGIN_STUDENT, "core-concepts", None),
                ("cookies", "core-concepts", None),
                ("open https://cybershop.training/account", "core-concepts", None),
                ("compare 3 5", "core-concepts", None),
                ("open https://cybershop.training/admin", "core-concepts", None),
                ("open -X POST https://cybershop.training/logout",
                 "core-concepts", None),
                ("open https://cybershop.training/admin", "core-concepts", None),
                ("open https://cybershop.training/api/me", "core-concepts", None),
                (('open -H "Authorization: Bearer training-token-001" '
                  "https://cybershop.training/api/me"), "core-concepts", None),
                (('open -H "Authorization: Bearer wrong-token" '
                  "https://cybershop.training/api/me"), "core-concepts", None),
                ("requests", "core-concepts", None),
                ("open https://cybershop.training/nothing-here",
                 "core-concepts", None),
                ("compare 6 8", "core-concepts", None),
            ],
            # Hands-on Practice §3-§9 — the six exercises, in order, as
            # one session. Introduction §10's history excerpt is checked
            # against this session's own `requests` output too (below).
            "hands": [
                ("web", "hands-on-practice", None),
                ("proxy", "hands-on-practice", None),
                ("open https://cybershop.training/products?id=42",
                 "hands-on-practice", None),
                ("headers", "hands-on-practice", None),
                ("requests", "hands-on-practice", None),
                ("intercept on", "hands-on-practice", None),
                ("open https://cybershop.training/products?id=42",
                 "hands-on-practice", None),
                ("forward", "hands-on-practice", None),
                ("intercept off", "hands-on-practice", None),
                ("repeater 1", "hands-on-practice", None),
                ("edit query id 43", "hands-on-practice", None),
                ("repeater send", "hands-on-practice", None),
                ("compare 1 3", "hands-on-practice", None),
                ("open https://cybershop.training/account",
                 "hands-on-practice", None),
                (self._LOGIN_STUDENT, "hands-on-practice", None),
                ("cookies", "hands-on-practice", None),
                ("open https://cybershop.training/account",
                 "hands-on-practice", None),
                ("compare 4 6", "hands-on-practice", None),
                ("open https://cybershop.training/admin",
                 "hands-on-practice", None),
                ("open -X POST https://cybershop.training/logout",
                 "hands-on-practice", None),
                ("open https://cybershop.training/admin",
                 "hands-on-practice", None),
                (self._LOGIN_ADMIN, "hands-on-practice", None),
                ("open https://cybershop.training/admin",
                 "hands-on-practice", None),
                ("compare 7 11", "hands-on-practice", None),
                # §9 step 1 shows these two commands without their output.
                ("open -X POST https://cybershop.training/logout", None, None),
                (self._LOGIN_STUDENT, None, None),
                ("open https://cybershop.training/api/profile",
                 "hands-on-practice", None),
                (self._POST_WRONG_KEY, "hands-on-practice", None),
                ("open https://cybershop.training/api/profile",
                 "hands-on-practice", None),
                (self._POST_RIGHT_KEY, "hands-on-practice", None),
                ("open https://cybershop.training/api/profile",
                 "hands-on-practice", None),
                ("requests", "hands-on-practice", None),
                ("compare 15 17", "hands-on-practice", None),
                ("open https://evil.example.com/", "hands-on-practice", None),
            ],
        }

    def test_quoted_proxy_output_matches_the_real_simulator(self, app):
        """Every request, response, history listing, Repeater send and
        response comparison quoted in all three lessons was captured by
        actually running the real terminal command handlers against the
        real WebLab the Burp Suite Fundamentals mission loads. If the
        simulator's routes, responses or output formatting ever change,
        the lessons become fabricated evidence — fail here rather than
        ship a lie."""
        raws = {slug: self._raw_lesson(slug) for slug in self._SLUGS}
        for name, steps in self._sessions().items():
            sh = self._shell()
            for index, (command, slug, window) in enumerate(steps):
                output = sh.execute(command)
                if slug is None:
                    continue
                lines = output.splitlines()
                if window is not None:
                    lines = lines[window[0]:window[1]]
                    assert lines, (
                        f"{name}#{index}: partial slice for `{command}` is empty"
                    )
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    assert line in raws[slug], (
                        f"{slug}: quoted output no longer matches the real "
                        f"simulator for `{command}` (session {name}, step "
                        f"{index}) — {line!r}"
                    )

    def test_introduction_history_excerpt_is_a_real_slice(self, app):
        """Introduction §10 quotes the first eleven entries of the real
        HTTP history built by the Hands-on Practice session. Replayed and
        checked as an actual line-slice so the excerpt can't drift."""
        raw = self._raw_lesson("introduction")
        sh = self._shell()
        output = ""
        for command, _slug, _window in self._sessions()["hands"]:
            result = sh.execute(command)
            if command == "requests":
                output = result
        lines = output.splitlines()[0:12]
        assert len(lines) == 12
        for line in lines:
            line = line.strip()
            if not line:
                continue
            assert line in raw, (
                f"introduction: history excerpt drifted from the real "
                f"simulator — {line!r}"
            )

    def test_out_of_scope_host_is_really_refused(self, app):
        """Both Introduction §11 and Hands-on §2 claim the simulator can
        never reach a host outside the training scope. Asserted, not
        assumed — and asserted on the state, not only the message."""
        sh = self._shell()
        before = len(sh.web_lab.session.history)
        out = sh.execute("open https://evil.example.com/")
        assert out == "External hosts are not available in the training environment."
        assert len(sh.web_lab.session.history) == before
        assert sh.web_lab.proxy.blocked_count == 1

    def test_silent_ignore_bug_investigated_in_lesson_is_real(self, app):
        """Hands-on §9's whole investigation rests on POST /api/profile
        accepting `Display_Name` with 200 OK while storing nothing, and
        `display_name` actually persisting. If the simulator is ever
        fixed, the lesson's finding becomes fiction."""
        import json

        sh = self._shell()
        sh.execute(self._LOGIN_STUDENT)
        sh.execute(self._POST_WRONG_KEY)
        _req, resp = (sh.web_lab.session.last_request,
                      sh.web_lab.session.last_response)
        assert resp.status_code == 200
        assert json.loads(resp.body)["display_name"] == "student"
        sh.execute(self._POST_RIGHT_KEY)
        resp = sh.web_lab.session.last_response
        assert resp.status_code == 200
        assert json.loads(resp.body)["display_name"] == "Alex Rivera"

    def test_admin_route_really_distinguishes_401_from_403(self, app):
        """Core Concepts §10 and Hands-on §8 both teach authentication vs.
        authorization from GET /admin returning 401 / 403 / 200. Pinned
        against the real simulator."""
        sh = self._shell()
        sh.execute("open https://cybershop.training/admin")
        assert sh.web_lab.session.last_response.status_code == 401
        sh.execute(self._LOGIN_STUDENT)
        sh.execute("open https://cybershop.training/admin")
        assert sh.web_lab.session.last_response.status_code == 403
        sh.execute("open -X POST https://cybershop.training/logout")
        sh.execute(self._LOGIN_ADMIN)
        sh.execute("open https://cybershop.training/admin")
        assert sh.web_lab.session.last_response.status_code == 200

    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="burp-suite").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in self._SLUGS:
                r = c.get(f"/roadmap/burp-suite/{slug}/")
                assert r.status_code == 200
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower()
                assert "<pre>" in body
                # No terminal free-practice CTA anywhere in this module.
                assert "Try it in the Terminal" not in body
            r = c.get("/roadmap/burp-suite/core-concepts/")
            body = r.data.decode("utf-8")
            assert "/terminal/mission/burp-fundamentals" in body
            assert "/labs/websec-http" not in body
            r = c.get("/roadmap/burp-suite/hands-on-practice/")
            body = r.data.decode("utf-8")
            assert "/terminal/mission/burp-fundamentals" in body
            assert "/labs/websec-http" in body
            assert "HTTP Requests &amp; Responses" in body
            r = c.get("/roadmap/burp-suite/introduction/")
            body = r.data.decode("utf-8")
            assert "/terminal/mission/burp-fundamentals" not in body
            assert "/labs/websec-http" not in body

    def test_cybermentor_receives_lesson_context(self, app, student):
        uname, uid = student
        with app.app_context():
            from app.extensions import db
            from app.roadmap.models import RoadmapModule, UserModuleProgress
            module = RoadmapModule.query.filter_by(slug="burp-suite").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug, title in (("introduction", "Introduction"),
                                ("core-concepts", "Core Concepts"),
                                ("hands-on-practice", "Hands-on Practice")):
                r = c.get(f"/roadmap/burp-suite/{slug}/")
                body = r.data.decode("utf-8")
                assert f'data-mentor-lab="Burp Suite — {title}"' in body

    def test_completion_awards_xp_exactly_once(self, app, student):
        """Completing a Burp Suite lesson awards its XP once; a repeat
        POST (the refresh case) must not award it again."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="burp-suite").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()
            before = User.query.get(uid).xp

        with app.test_client() as c:
            _login(c, uname)
            c.post("/roadmap/burp-suite/core-concepts/complete", follow_redirects=True)
            with app.app_context():
                after_first = User.query.get(uid).xp
            c.post("/roadmap/burp-suite/core-concepts/complete", follow_redirects=True)
            with app.app_context():
                after_second = User.query.get(uid).xp

        assert after_first == before + 50, "core-concepts should award exactly 50 XP"
        assert after_second == after_first, "XP awarded twice for one lesson"

    def test_module_completion_awards_bonus_and_unlocks_owasp(self, app):
        """A dedicated user completes all three Burp Suite lessons: 25 +
        50 + 100 lesson XP + 175 module bonus = 350, awarded once, and
        `owasp-top-10` (Intermediate #4) becomes available."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress
        from app.roadmap.services import complete_lesson, module_status

        with app.app_context():
            u = User(username="burp_module_complete", email="burp_complete@t.io")
            u.set_password("Str0ngPass!")
            db.session.add(u)
            db.session.commit()
            uid = u.id

            module = RoadmapModule.query.filter_by(slug="burp-suite").first()
            db.session.add(UserModuleProgress(
                user_id=uid, module_id=module.id, unlocked=True))
            db.session.commit()

            before = User.query.get(uid).xp
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                complete_lesson(User.query.get(uid), "burp-suite", slug)
            after = User.query.get(uid).xp
            assert after == before + 350

            # Re-completing must not award anything again.
            for slug in ("introduction", "core-concepts", "hands-on-practice"):
                result = complete_lesson(User.query.get(uid), "burp-suite", slug)
                assert result["already_completed"] is True
                assert result["xp_awarded"] == 0
            assert User.query.get(uid).xp == after

            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            assert row.completed is True
            assert row.bonus_awarded is True

            nxt = RoadmapModule.query.filter_by(slug="owasp-top-10").first()
            assert module_status(User.query.get(uid), nxt) == "available"


# ═══════════════════════════════════════════
# Content — OWASP Top 10 (YC-037.4)
# ═══════════════════════════════════════════
class TestOwaspTop10Content:
    """Guards the real content written for YC-037.4 — OWASP Top 10,
    module 4 of Intermediate. Pins that each lesson teaches its actual
    material, that the module commits to exactly one OWASP edition
    (2021) with no other edition's category names mixed in, that every
    quoted request/response/query/header block is byte-for-byte what
    this platform's real simulated web application
    (`app/core/terminal/web.py`, driven through the real `open`/`web`/
    `headers`/`cookies`/`schema`/`query`/`expire`/`requests` command
    handlers in `app/core/terminal/commands.py`) actually produces, and
    that the module's mission links (`authentication-sessions` on
    core-concepts, `sql-injection-fundamentals` on hands-on-practice)
    and lab link (`websec-http` on hands-on-practice) are real,
    reachable routes."""

    _SLUGS: ClassVar[tuple[str, ...]] = (
        "introduction", "core-concepts", "hands-on-practice",
    )

    # The 2021 edition's ten categories, exactly as the module must name
    # them. Losing or renaming one silently mixes editions.
    _CATEGORIES_2021: ClassVar[tuple[tuple[str, str], ...]] = (
        ("A01", "Broken Access Control"),
        ("A02", "Cryptographic Failures"),
        ("A03", "Injection"),
        ("A04", "Insecure Design"),
        ("A05", "Security Misconfiguration"),
        ("A06", "Vulnerable and Outdated Components"),
        ("A07", "Identification and Authentication Failures"),
        ("A08", "Software and Data Integrity Failures"),
        ("A09", "Security Logging and Monitoring Failures"),
        ("A10", "Server-Side Request Forgery"),
    )

    # Category names that belong to OTHER editions only. If one of these
    # appears in the teaching lessons the module has silently drifted.
    _OTHER_EDITION_NAMES: ClassVar[tuple[str, ...]] = (
        "Sensitive Data Exposure",
        "XML External Entities",
        "Broken Authentication",
        "Insecure Deserialization",
        "Using Components with Known Vulnerabilities",
        "Insufficient Logging",
    )

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "OWASP Top 10 – 2021", "attack surface", "trust boundary",
            "Validation", "Sanitisation", "Encoding",
            "awareness document", "allowlist",
            "OBSERVATION", "INTERPRETATION", "CONCLUSION",
            "Authorization Boundary", "baseline",
        ],
        "core-concepts": [
            "Authentication", "Authorization", "401", "403", "200",
            "parameterised", "placeholder", "prepared statement",
            "SELECT * FROM products WHERE name = ?",
            "Cross-Site Request Forgery", "SameSite",
            "csrf_token", "session identifier",
            "abuse case", "defence in depth", "allowlist",
            "OBSERVATION", "INTERPRETATION", "CONCLUSION",
            "illustrative only, not captured output",
        ],
        "hands-on-practice": [
            "Authorization Comes First", "SEVERITY REASONING",
            "VALIDATION STRATEGY", "CONFIDENCE", "NOT TESTED",
            "OBSERVATION", "INTERPRETATION", "CONCLUSION",
            "baseline", "one variable",
            "illustrative example, not captured output",
        ],
    }

    # The exact WRONG/CORRECT corrections the driving spec named. Losing
    # any of these makes the module technically wrong, not merely thinner.
    _REQUIRED_CORRECTIONS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "The OWASP Top 10 contains every vulnerability that matters.",
            "It is a risk-awareness framework covering ten categories",
            "If I'm authenticated, I'm allowed.",
            "Authentication establishes <em>who you are</em>",
            "This parameter takes user input, so it's vulnerable.",
            "The application returned 403, so authorization is secure.",
            "HTTPS solves web security.",
            "The button isn't shown to this user, so this user can't do it.",
        ],
        "core-concepts": [
            "An old version is not automatically vulnerable.",
            "Injection means SQL injection.",
            "Filtering dangerous characters prevents injection.",
            "A 500 error proves SQL injection.",
            "If it's behind a login, it's protected.",
            "That's just the browser making a request.",
            "in SSRF, the <em>server</em> makes the request",
            "Checking the file extension is enough.",
        ],
    }

    @staticmethod
    def _render(app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(
                f"roadmap/intermediate/owasp-top-10/{slug}.md"
            )

    @staticmethod
    def _raw_lesson(slug):
        from pathlib import Path

        import app as app_pkg
        path = (Path(app_pkg.__file__).parent / "content" / "roadmap"
                / "intermediate" / "owasp-top-10" / f"{slug}.md")
        return path.read_text(encoding="utf-8")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in self._SLUGS:
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
            assert len(html) > 3000, f"{slug}: suspiciously short ({len(html)} chars)"

    def test_lessons_contain_their_taught_terms(self, app):
        for slug, terms in self._EXPECTED_TERMS.items():
            html = self._render(app, slug)
            for term in terms:
                assert term in html, f"{slug}: missing expected term {term!r}"

    def test_lessons_keep_their_misconception_corrections(self, app):
        for slug, claims in self._REQUIRED_CORRECTIONS.items():
            html = self._render(app, slug)
            for claim in claims:
                assert claim in html, f"{slug}: lost required correction {claim!r}"

    def test_lessons_contain_real_code_examples(self, app):
        for slug in self._SLUGS:
            html = self._render(app, slug)
            assert "<pre>" in html and "<code>" in html, f"{slug}: no code block rendered"

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        """Same guard every prior content pass uses, with one deliberate
        narrowing: the bare word "placeholder" is a *taught term* in this
        module (a parameterised query binds its data into a placeholder —
        Core Concepts §12), so unfinished-content detection matches the
        phrases that actually signal unfinished content instead."""
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder content",
                  "placeholder text", "this is a placeholder",
                  "to be written", "tbd")
        for slug in self._SLUGS:
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    # ── Edition discipline ─────────────────────────────────────────────
    def test_module_declares_the_2021_edition_explicitly(self, app):
        """The repository pins no OWASP edition anywhere (verified during
        YC-037.4's inspection pass), so the module has to say which one it
        teaches rather than leaving a reader to guess."""
        intro = self._raw_lesson("introduction")
        assert "This module teaches the OWASP Top 10 – 2021 edition" in intro
        assert "Always state the edition when you cite a category." in intro
        assert "Check which edition is current before you write a professional report." in intro
        assert "OWASP Top 10 – 2021" in self._raw_lesson("core-concepts")

    def test_all_ten_2021_categories_are_taught_by_their_real_names(self, app):
        core = self._render(app, "core-concepts")
        intro = self._render(app, "introduction")
        for ident, name in self._CATEGORIES_2021:
            assert name in core, f"core-concepts: 2021 category {name!r} missing"
            assert name in intro, f"introduction: 2021 category {name!r} missing"
            assert f"{ident}:2021" in core, (
                f"core-concepts: identifier {ident}:2021 missing"
            )

    def test_no_other_edition_category_names_are_mixed_in(self, app):
        """Editions must not be blended. These names belong to editions
        other than 2021, and are permitted *only* where a lesson is
        explicitly explaining that a category was renamed between
        editions — twice in the introduction's edition-history paragraph,
        and twice in Core Concepts, where §8 and §21 each name the former
        title of the category they introduce (both explicitly attributed
        to the older edition). Every other occurrence, and every other
        name, is drift."""
        intro = self._raw_lesson("introduction")
        core = self._raw_lesson("core-concepts")
        hands = self._raw_lesson("hands-on-practice")

        # The three permitted, rename-explaining mentions, pinned exactly.
        assert intro.count("Broken Authentication") == 1
        assert intro.count("Sensitive Data Exposure") == 1
        assert '"Identification and Authentication Failures" in 2021' in intro
        assert core.count("Sensitive Data Exposure") == 1
        assert 'renamed this category from "Sensitive Data Exposure"' in core
        assert core.count("Broken Authentication") == 1
        assert 'Renamed from 2017\'s "Broken Authentication"' in core

        allowed = {
            "introduction": {"Broken Authentication": 1,
                             "Sensitive Data Exposure": 1},
            "core-concepts": {"Broken Authentication": 1,
                              "Sensitive Data Exposure": 1},
            "hands-on-practice": {},
        }
        for slug, raw in (("introduction", intro), ("core-concepts", core),
                          ("hands-on-practice", hands)):
            for name in self._OTHER_EDITION_NAMES:
                assert raw.count(name) == allowed[slug].get(name, 0), (
                    f"{slug}: other-edition name {name!r} appears "
                    f"{raw.count(name)} time(s), expected "
                    f"{allowed[slug].get(name, 0)}"
                )

    def test_top_ten_is_taught_as_non_exhaustive(self, app):
        intro = self._render(app, "introduction")
        assert "Why the Top 10 Is Not a Complete List" in intro
        assert "business logic" in intro.lower()
        assert "race condition" in intro.lower()

    # ── Core reasoning the module exists to install ───────────────────
    def test_authentication_versus_authorization_is_taught(self, app):
        intro = self._render(app, "introduction")
        core = self._render(app, "core-concepts")
        assert "Authentication Is Not Authorization" in core
        for html in (intro, core):
            assert "who are you?" in html
        assert ("You are authenticated, but not authorized to access this "
                "resource.") in core

    def test_client_side_is_never_a_security_boundary(self, app):
        """The single most load-bearing claim in the module."""
        intro = self._render(app, "introduction")
        assert ("A restriction that exists only in the browser is not a "
                "security control.") in intro

    def test_parameterised_queries_taught_as_the_injection_defence(self, app):
        core = self._render(app, "core-concepts")
        assert ("Parameterisation does not clean your input. It makes your "
                "input structurally incapable of being anything but data.") in core
        assert "Sanitisation is not a substitute for parameterised queries" in (
            self._render(app, "introduction")
        )

    def test_observation_interpretation_conclusion_used_in_every_lesson(self, app):
        for slug in self._SLUGS:
            html = self._render(app, slug)
            for word in ("OBSERVATION", "INTERPRETATION", "CONCLUSION"):
                assert word in html, f"{slug}: missing {word}"

    def test_finding_report_template_requires_evidence_and_impact(self, app):
        hands = self._render(app, "hands-on-practice")
        for field in ("FINDING:", "OWASP CATEGORY:", "AFFECTED ENDPOINT:",
                      "INPUT:", "ORIGINAL REQUEST:", "MODIFIED REQUEST:",
                      "OBSERVED RESPONSE:", "EVIDENCE:", "SECURITY IMPACT:",
                      "SEVERITY REASONING:", "RECOMMENDED FIX:",
                      "VALIDATION STRATEGY:", "CONFIDENCE:", "NOT TESTED:"):
            assert field in hands, f"hands-on-practice: report field {field!r} missing"

    def test_six_practical_exercises_exist(self, app):
        hands = self._render(app, "hands-on-practice")
        for heading in ("Exercise 1 — Broken Access Control",
                        "Exercise 2 — Injection",
                        "Exercise 3 — Identification and Authentication Failures",
                        "Exercise 4 — Security Misconfiguration",
                        "Exercise 5 — Server-Side Request Forgery",
                        "Exercise 6 — The Finding Report"):
            assert heading in hands, f"hands-on-practice: {heading!r} missing"

    # ── Safety ────────────────────────────────────────────────────────
    def test_no_unauthorized_or_offensive_framing(self, app):
        """Permanent safety rule: this module teaches authorized,
        evidence-driven web application testing. It must never drift into
        teaching session theft, credential attacks against real accounts,
        attacks on cloud metadata services, destructive injection, or
        detection evasion."""
        banned = ("steal the session", "steal a session", "hijack the session",
                  "steal the cookie", "forge a session", "forge the cookie",
                  "evade detection", "avoid being detected",
                  "drop table", "any public website", "any live site",
                  "169.254.169.254")
        for slug in self._SLUGS:
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains unsafe framing {phrase!r}"

    def test_authorization_boundary_is_stated(self, app):
        intro = self._render(app, "introduction")
        assert "The Authorization Boundary" in intro
        assert "explicit written permission" in intro
        hands = self._render(app, "hands-on-practice")
        assert "Authorization Comes First" in hands
        core = self._render(app, "core-concepts")
        for html, slug in ((intro, "introduction"), (core, "core-concepts"),
                           (hands, "hands-on-practice")):
            assert "authoriz" in html.lower(), f"{slug}: no authorization framing"

    def test_ssrf_is_taught_without_operational_attack_detail(self, app):
        """A10 has no runnable scenario on this platform. The lesson must
        say so, must label its one example as illustrative, and must not
        hand out operational detail for attacking internal networks."""
        core = self._raw_lesson("core-concepts")
        assert ("This platform has no SSRF scenario, and none is invented "
                "here.") in core
        assert "illustrative only, not captured output" in core
        hands = self._raw_lesson("hands-on-practice")
        assert ("this platform has no SSRF scenario and none is invented "
                "here") in hands
        assert "illustrative example, not captured output" in hands

    def test_categories_with_no_runnable_evidence_say_so(self, app):
        """A02, A09 and A10 cannot be demonstrated on this platform. Each
        must state that outright rather than quietly implying the absent
        material was covered."""
        core = self._raw_lesson("core-concepts")
        assert "This module has no runnable cryptographic evidence" in core, "A02"
        assert "The simulator models no server-side log at all" in core, "A09"
        assert "This platform has no SSRF scenario" in core, "A10"

    # ── Structure untouched ───────────────────────────────────────────
    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="owasp-top-10").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2, and
        the module still sits at Intermediate display_order 4."""
        from app.roadmap.models import Lesson, RoadmapCategory, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="owasp-top-10").first()
            assert module.id == 12
            assert module.display_order == 4
            intermediate = RoadmapCategory.query.filter_by(
                title="Intermediate").first()
            assert module.category_id == intermediate.id
            assert module.difficulty == "intermediate"
            assert module.estimated_hours == 1
            assert module.xp_reward == 175
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [lesson.id for lesson in lessons] == [34, 35, 36]
            assert [lesson.slug for lesson in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [lesson.display_order for lesson in lessons] == [1, 2, 3]
            assert [lesson.xp_reward for lesson in lessons] == [25, 50, 100]
            assert [lesson.estimated_minutes for lesson in lessons] == [10, 20, 30]
            assert [lesson.content_path for lesson in lessons] == [
                "roadmap/intermediate/owasp-top-10/introduction.md",
                "roadmap/intermediate/owasp-top-10/core-concepts.md",
                "roadmap/intermediate/owasp-top-10/hands-on-practice.md",
            ]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_intermediate_module_order_unchanged(self, app):
        """Nmap < Wireshark < Burp Suite < OWASP Top 10, still 1/2/3/4."""
        from app.roadmap.models import RoadmapCategory, RoadmapModule

        with app.app_context():
            intermediate = RoadmapCategory.query.filter_by(
                title="Intermediate").first()
            order = [
                (m.slug, m.display_order) for m in
                RoadmapModule.query.filter_by(category_id=intermediate.id)
                .order_by(RoadmapModule.display_order).limit(5).all()
            ]
            assert order == [("nmap", 1), ("wireshark", 2), ("burp-suite", 3),
                             ("owasp-top-10", 4),
                             ("active-directory-basics", 5)]

    # ── Practice links ────────────────────────────────────────────────
    def test_practice_links_are_scoped_and_no_terminal_link(self, app, student):
        """introduction has no practice CTA (its exercises are reasoning
        questions about output already printed in the lesson);
        core-concepts links the Authentication & Sessions mission;
        hands-on-practice links the SQL Injection Fundamentals mission and
        the HTTP Requests & Responses lab. No lesson offers the
        free-practice terminal."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        expected = {
            "introduction": (None, False),
            "core-concepts": ("authentication-sessions", False),
            "hands-on-practice": ("sql-injection-fundamentals", True),
        }
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, (mission, want_lab) in expected.items():
                ctx = get_lesson_view_context(student_user, "owasp-top-10", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert not practice.get("show_terminal"), slug
                assert practice.get("mission_slug") == mission, slug
                assert bool(practice.get("lab_slug")) is want_lab, slug
                if want_lab:
                    assert practice["lab_slug"] == "websec-http"
                    assert practice["lab_title"] == "HTTP Requests & Responses"

    def test_free_practice_terminal_really_has_no_web_lab(self, app):
        """The reason `owasp-top-10` is excluded from
        _TERMINAL_PRACTICE_MODULES, asserted rather than assumed."""
        from app.core.terminal.shell import Shell

        sh = Shell()
        assert sh.web_lab is None
        assert sh.execute("open https://cybershop.training/admin") == (
            "open: no simulated web environment configured for this session"
        )
        assert sh.execute("query") == (
            "query: no simulated web environment configured for this session"
        )

    def test_lab_link_points_to_a_real_reachable_lab(self, app):
        """`websec-http` is real, active, interactive AND has no
        prerequisite — the reason it is the one websec lab this module can
        link without producing a dead CTA."""
        with app.test_request_context():
            from flask import url_for
            assert url_for("labs.detail", slug="websec-http") == "/labs/websec-http"
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug="websec-http").first()
            assert lab is not None and lab.is_active and lab.is_interactive
            assert lab.title == "HTTP Requests & Responses"
            assert lab.prerequisite_lab_id is None

    def test_websec_lab_chain_named_in_lesson_is_real_and_really_gated(self, app):
        """hands-on §12 states the ten web-security labs unlock in a fixed
        order and names each by its real title. Both halves get verified:
        the labs exist with those titles, and the chain really is linear
        with `websec-http` as its only ungated entry."""
        raw = self._raw_lesson("hands-on-practice")
        chain = ["websec-http", "websec-cookies", "websec-sessions",
                 "websec-auth", "websec-idor", "websec-sqli", "websec-xss",
                 "websec-csrf", "websec-upload", "websec-headers"]
        with app.app_context():
            from app.labs.models import Lab
            previous = None
            for slug in chain:
                lab = Lab.query.filter_by(slug=slug).first()
                assert lab is not None and lab.is_active, f"{slug}: not a real lab"
                assert lab.title in raw, (
                    f"{slug}: lesson names a title the database does not have "
                    f"({lab.title!r})"
                )
                if previous is None:
                    assert lab.prerequisite_lab_id is None, (
                        "websec-http is the chain entry and must stay ungated"
                    )
                else:
                    assert lab.prerequisite_lab_id == previous.id, (
                        f"{slug}: chain order drifted from the lesson's claim"
                    )
                previous = lab

    def test_mission_links_point_to_real_routes_and_real_missions(self, app):
        from app.core.missions.mission_loader import MISSIONS

        with app.test_request_context():
            from flask import url_for
            for slug in ("authentication-sessions", "sql-injection-fundamentals"):
                assert url_for("terminal.mission_page", slug=slug) == (
                    f"/terminal/mission/{slug}"
                )
        auth = MISSIONS["authentication-sessions"]
        assert auth["title"] == "Authentication & Sessions"
        assert len(auth["objectives"]) == 15
        assert auth["web_lab"] == "auth-lifecycle"
        sqli = MISSIONS["sql-injection-fundamentals"]
        assert sqli["title"] == "SQL Injection Fundamentals"
        assert len(sqli["objectives"]) == 16
        assert sqli["web_lab"] == "sqli-investigation"

    def test_further_missions_named_in_lesson_text_are_real(self, app):
        """hands-on §12 names the other three web-security missions by
        title. Naming a mission is a claim about reality even when it is
        not a link."""
        from app.core.missions.mission_loader import MISSIONS

        raw = self._raw_lesson("hands-on-practice")
        for slug in ("xss-fundamentals", "csrf-fundamentals",
                     "file-upload-security"):
            assert slug in MISSIONS, f"{slug}: not a real mission"
            assert MISSIONS[slug]["title"] in raw, (
                f"{slug}: lesson names a title the loader does not have "
                f"({MISSIONS[slug]['title']!r})"
            )

    def test_soc_lab_named_for_a09_is_real_and_ungated(self, app):
        """Core Concepts §26 and hands-on §12 both point at the real SOC
        brute-force lab as the one place on this platform where the
        defending side of A09 can be seen. Both claims — that it exists
        and that it is reachable — are verified."""
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug="soc-brute-force").first()
            assert lab is not None and lab.is_active and lab.is_interactive
            assert lab.prerequisite_lab_id is None
            assert lab.title == "SOC: Brute Force Investigation"
        for slug in ("core-concepts", "hands-on-practice"):
            assert "SOC: Brute Force Investigation" in self._raw_lesson(slug)

    def test_training_credentials_named_in_lessons_are_the_real_ones(self, app):
        """Every credential printed in these lessons is a fixed, fictional
        training constant defined in the simulator."""
        from app.core.terminal.web import _USERS, API_TOKEN, HOST

        assert HOST == "cybershop.training"
        assert _USERS["student"] == "training123"
        assert _USERS["admin"] == "admin123"
        assert _USERS["analyst"] == "analyst123"
        assert API_TOKEN == "training-token-001"
        for slug in self._SLUGS:
            assert "cybershop.training" in self._raw_lesson(slug)
        for slug in ("core-concepts", "hands-on-practice"):
            raw = self._raw_lesson(slug)
            for value in ("student", "training123", "admin", "admin123",
                          "analyst", "analyst123"):
                assert value in raw, f"{slug}: {value!r} not named"

    # ── Real-evidence guard ────────────────────────────────────────────
    _LOGIN_STUDENT: ClassVar[str] = (
        'open -X POST -d "username=student&password=training123" '
        "https://cybershop.training/auth/login"
    )
    _LOGIN_ADMIN: ClassVar[str] = (
        'open -X POST -d "username=admin&password=admin123" '
        "https://cybershop.training/auth/login"
    )
    _LOGIN_BAD: ClassVar[str] = (
        'open -X POST -d "username=student&password=wrong-password" '
        "https://cybershop.training/auth/login"
    )
    _SEARCH_QUOTE: ClassVar[str] = (
        "open \"https://cybershop.training/search?q='\""
    )
    _SEARCH_TRUE: ClassVar[str] = (
        "open \"https://cybershop.training/search?q=' OR '1'='1\""
    )
    _SECURE_SEARCH_TRUE: ClassVar[str] = (
        "open \"https://cybershop.training/secure-search?q=' OR '1'='1\""
    )
    _BYPASS_LOGIN: ClassVar[str] = (
        "open -X POST -d \"username=admin'--&password=anything\" "
        "https://cybershop.training/training-login"
    )
    _BYPASS_SECURE_LOGIN: ClassVar[str] = (
        "open -X POST -d \"username=admin'--&password=anything\" "
        "https://cybershop.training/secure-login"
    )
    _TRANSFER: ClassVar[str] = (
        'open -X POST -d "amount=100&recipient=training-user" '
        "https://cybershop.training/transfer"
    )
    _TRANSFER_FORGED: ClassVar[str] = (
        'open -X POST -H "Origin: https://attacker.training" '
        '-d "amount=100&recipient=training-user" '
        "https://cybershop.training/transfer"
    )
    _SECURE_TRANSFER_FORGED: ClassVar[str] = (
        'open -X POST -H "Origin: https://attacker.training" '
        '-d "amount=100&recipient=training-user'
        '&csrf_token=TRAINING_TOKEN_STUDENT_SESSION" '
        "https://cybershop.training/secure-transfer"
    )
    _SECURE_TRANSFER_NO_TOKEN: ClassVar[str] = (
        'open -X POST -d "amount=100&recipient=training-user" '
        "https://cybershop.training/secure-transfer"
    )
    _SECURE_TRANSFER_OK: ClassVar[str] = (
        'open -X POST -d "amount=100&recipient=training-user'
        '&csrf_token=TRAINING_TOKEN_STUDENT_SESSION" '
        "https://cybershop.training/secure-transfer"
    )
    _UPLOAD_SHELL: ClassVar[str] = (
        'open -X POST -d "filename=shell.php.jpg" '
        "https://cybershop.training/upload"
    )
    _SECURE_UPLOAD_SHELL: ClassVar[str] = (
        'open -X POST -d "filename=shell.php.jpg" '
        "https://cybershop.training/secure-upload"
    )

    @staticmethod
    def _shell(scenario):
        from app.core.terminal.shell import Shell
        from app.core.terminal.web import build_web_lab

        sh = Shell()
        sh.web_lab = build_web_lab(scenario)
        return sh

    def _sessions(self):
        """Each session is an ordered command list replayed on one shell,
        mirroring exactly how the lessons present them. Entries are
        (command, lesson-slug-or-None): None marks a setup step the lesson
        deliberately does not quote."""
        intro, core, hands = self._SLUGS
        return {
            # Introduction §3 and §8.
            "intro": ("sqli-investigation", [
                ("web", intro),
                ("open https://evil.example.com/", intro),
            ]),
            # Core Concepts §4-§24, one continuous session: the balances
            # and session states in the quoted output only line up if the
            # steps run in exactly this order.
            "core": ("sqli-investigation", [
                ("open https://cybershop.training/admin", core),
                (self._LOGIN_STUDENT, core),
                ("open https://cybershop.training/admin", core),
                ("open https://cybershop.training/account", None),
                ("open -X POST https://cybershop.training/logout", core),
                ("open https://cybershop.training/account", core),
                (self._LOGIN_ADMIN, core),
                ("open https://cybershop.training/admin", core),
                ("open -X POST https://cybershop.training/logout", None),
                ("open https://cybershop.training/products?id=42", None),
                ("headers", core),
                (self._LOGIN_STUDENT, None),
                ("open https://cybershop.training/profile", None),
                ("headers", core),
                ("schema products", core),
                ("open https://cybershop.training/search?q=Laptop", core),
                ("query", core),
                (self._SEARCH_QUOTE, core),
                ("query", core),
                (self._SEARCH_TRUE, core),
                ("query", core),
                (self._SECURE_SEARCH_TRUE, core),
                ("query", core),
                (self._BYPASS_LOGIN, core),
                ("query", core),
                (self._BYPASS_SECURE_LOGIN, core),
                ("query", core),
                ("open https://cybershop.training/search?q=<TRAINING_XSS>", core),
                ("open https://cybershop.training/secure-search?q=<TRAINING_XSS>",
                 core),
                ("open https://cybershop.training/csrf-demo", core),
                (self._TRANSFER, core),
                (self._TRANSFER_FORGED, core),
                ("open https://cybershop.training/secure-transfer", core),
                (self._SECURE_TRANSFER_FORGED, core),
                (self._SECURE_TRANSFER_NO_TOKEN, core),
                (self._SECURE_TRANSFER_OK, core),
                ("open https://cybershop.training/nothing-here", core),
                (self._LOGIN_BAD, core),
                ("expire", core),
                ("open https://cybershop.training/profile", core),
                (self._LOGIN_STUDENT, None),
                ("open https://cybershop.training/upload-security", core),
                (self._UPLOAD_SHELL, core),
                (self._SECURE_UPLOAD_SHELL, core),
                ("open https://cybershop.training/uploads", core),
            ]),
            # Hands-on Practice §4-§9 — the exercises in order, as one
            # session, which is what makes §9's request history real.
            "hands": ("auth-lifecycle", [
                ("web", hands),
                ("open https://cybershop.training/admin", hands),
                (self._LOGIN_STUDENT, hands),
                ("cookies", hands),
                ("open https://cybershop.training/admin", hands),
                ("open https://cybershop.training/profile", hands),
                (self._LOGIN_ADMIN, hands),
                ("open https://cybershop.training/admin", hands),
                ("open -X POST https://cybershop.training/logout", hands),
                ("schema", hands),
                ("open https://cybershop.training/search?q=Monitor", hands),
                ("query", hands),
                (self._SEARCH_QUOTE, hands),
                ("query", hands),
                (self._SEARCH_TRUE, hands),
                ("query", hands),
                (self._SECURE_SEARCH_TRUE, hands),
                ("query", hands),
                (self._LOGIN_BAD, hands),
                (self._LOGIN_STUDENT, hands),
                ("open https://cybershop.training/profile", hands),
                ("expire", hands),
                ("open https://cybershop.training/profile", hands),
                (self._LOGIN_STUDENT, hands),
                ("open https://cybershop.training/products?id=42", hands),
                ("headers", hands),
                ("open https://cybershop.training/nothing-here", hands),
                ("open https://evil.example.com/", hands),
                ("requests", hands),
            ]),
        }

    def test_quoted_simulator_output_matches_the_real_simulator(self, app):
        """Every request, response, header listing, schema dump, query
        visualisation and request history quoted in all three lessons was
        captured by actually running the real terminal command handlers
        against the real simulated web application. If the simulator's
        routes, responses or output formatting ever change, the lessons
        become fabricated evidence — fail here rather than ship a lie."""
        raws = {slug: self._raw_lesson(slug) for slug in self._SLUGS}
        for name, (scenario, steps) in self._sessions().items():
            sh = self._shell(scenario)
            for index, (command, slug) in enumerate(steps):
                output = sh.execute(command)
                if slug is None:
                    continue
                for line in output.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    assert line in raws[slug], (
                        f"{slug}: quoted output no longer matches the real "
                        f"simulator for `{command}` (session {name}, step "
                        f"{index}) — {line!r}"
                    )

    def test_admin_route_really_distinguishes_401_403_and_200(self, app):
        """Exercise 1's entire conclusion rests on one URL producing three
        outcomes as a function of session identity alone."""
        sh = self._shell("auth-lifecycle")
        assert "401 Unauthorized" in sh.execute(
            "open https://cybershop.training/admin")
        sh.execute(self._LOGIN_STUDENT)
        assert "403 Forbidden" in sh.execute(
            "open https://cybershop.training/admin")
        sh.execute(self._LOGIN_ADMIN)
        assert "200 OK" in sh.execute("open https://cybershop.training/admin")

    def test_injection_endpoints_really_differ(self, app):
        """Core Concepts §11-§13 and Exercise 2 both rest on /search being
        concatenated and /secure-search being parameterised. Asserted on
        the simulator's own behaviour, not only on the quoted text."""
        sh = self._shell("sqli-investigation")
        vulnerable = sh.execute(self._SEARCH_TRUE)
        assert "X-Sim-Query-Kind: boolean_true" in vulnerable
        assert "4 match(es)" in vulnerable
        secure = sh.execute(self._SECURE_SEARCH_TRUE)
        assert "X-Sim-Query-Kind: parameterized" in secure
        assert "SELECT * FROM products WHERE name = ?" in secure
        assert "0 match(es)" in secure
        assert "X-Sim-Query-Kind: auth_bypass" in sh.execute(self._BYPASS_LOGIN)
        assert "401 Unauthorized" in sh.execute(self._BYPASS_SECURE_LOGIN)

    def test_session_expiry_really_rejects_an_unchanged_request(self, app):
        """Exercise 3's whole point: the client sends a byte-identical
        request and the server rejects it, because the server decides."""
        sh = self._shell("auth-lifecycle")
        sh.execute(self._LOGIN_STUDENT)
        before = sh.execute("open https://cybershop.training/profile")
        assert "200 OK" in before
        assert "Cookie: session_id=student-session" in before
        sh.execute("expire")
        after = sh.execute("open https://cybershop.training/profile")
        assert "401 Unauthorized" in after
        assert "Cookie: session_id=student-session" in after

    def test_out_of_scope_host_is_really_refused(self, app):
        """Introduction §3 and Exercise 5 both claim the environment can
        never reach a host outside the training scope. Asserted on state,
        not only on the message."""
        sh = self._shell("sqli-investigation")
        before = len(sh.web_lab.session.history)
        out = sh.execute("open https://evil.example.com/")
        assert out == "External hosts are not available in the training environment."
        assert len(sh.web_lab.session.history) == before
        assert sh.web_lab.proxy.blocked_count == 1

    def test_simulator_really_has_no_per_user_resource_endpoint(self, app):
        """Core Concepts §6 and Exercise 1 both say outright that the
        horizontal/IDOR test cannot be run here. If a per-user resource
        endpoint is ever added, that honesty note becomes wrong and this
        test should fail so the lessons get updated."""
        from app.core.terminal.web import HOST

        sh = self._shell("sqli-investigation")
        sh.execute(self._LOGIN_STUDENT)
        routes = sh.execute("web")
        assert HOST in routes
        assert "/orders/" not in routes
        for path in ("/orders/1041", "/orders/1042", "/users/1", "/api/users/1"):
            out = sh.execute(f"open https://{HOST}{path}")
            assert "404 Not Found" in out, f"{path} unexpectedly exists"

    # ── Rendering, XP and progression ─────────────────────────────────
    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="owasp-top-10").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in self._SLUGS:
                r = c.get(f"/roadmap/owasp-top-10/{slug}/")
                assert r.status_code == 200, slug
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower(), slug

    def test_cybermentor_context_is_set_on_every_lesson_page(self, app, student):
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="owasp-top-10").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug, title in (("introduction", "Introduction"),
                                ("core-concepts", "Core Concepts"),
                                ("hands-on-practice", "Hands-on Practice")):
                r = c.get(f"/roadmap/owasp-top-10/{slug}/")
                body = r.data.decode("utf-8")
                assert f'data-mentor-lab="OWASP Top 10 — {title}"' in body

    def test_completion_awards_xp_exactly_once(self, app, student):
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(slug="owasp-top-10").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()
            before = User.query.get(uid).xp

        with app.test_client() as c:
            _login(c, uname)
            c.post("/roadmap/owasp-top-10/core-concepts/complete",
                   follow_redirects=True)
            with app.app_context():
                after_first = User.query.get(uid).xp
            c.post("/roadmap/owasp-top-10/core-concepts/complete",
                   follow_redirects=True)
            with app.app_context():
                after_second = User.query.get(uid).xp

        assert after_first == before + 50, "core-concepts should award exactly 50 XP"
        assert after_second == after_first, "XP awarded twice for one lesson"

    def test_module_completion_awards_bonus_and_unlocks_active_directory(self, app):
        """A dedicated user completes all three OWASP Top 10 lessons:
        25 + 50 + 100 lesson XP + 175 module bonus = 350, awarded once,
        and `active-directory-basics` (Intermediate #5) becomes
        available."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress
        from app.roadmap.services import complete_lesson, module_status

        with app.app_context():
            u = User(username="owasp_module_complete", email="owasp_complete@t.io")
            u.set_password("Str0ngPass!")
            db.session.add(u)
            db.session.commit()
            uid = u.id

            module = RoadmapModule.query.filter_by(slug="owasp-top-10").first()
            db.session.add(UserModuleProgress(
                user_id=uid, module_id=module.id, unlocked=True))
            db.session.commit()

            before = User.query.get(uid).xp
            for slug in self._SLUGS:
                complete_lesson(User.query.get(uid), "owasp-top-10", slug)
            after = User.query.get(uid).xp
            assert after == before + 350

            for slug in self._SLUGS:
                result = complete_lesson(User.query.get(uid), "owasp-top-10", slug)
                assert result["already_completed"] is True
                assert result["xp_awarded"] == 0
            assert User.query.get(uid).xp == after

            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            assert row.completed is True
            assert row.bonus_awarded is True

            nxt = RoadmapModule.query.filter_by(
                slug="active-directory-basics").first()
            assert module_status(User.query.get(uid), nxt) == "available"


# ═══════════════════════════════════════════
# Content — Active Directory Basics (YC-037.5)
# ═══════════════════════════════════════════
class TestActiveDirectoryContent:
    """Guards the real content written for YC-037.5 — Active Directory
    Basics, module 5 of Intermediate. Pins that each lesson teaches its
    actual material, that the terminology distinctions this module exists
    to install survive (AD vs AD DS vs Domain Controller; LDAP vs
    Kerberos; TGT vs service ticket; GPO vs OU; authentication vs
    authorization), that every quoted console block is byte-for-byte what
    this platform's real AD simulator (`app/labs/ad/`) actually produces,
    and that the module's lab link (`ad-orientation`, on core-concepts and
    hands-on-practice) is a real, reachable, ungated route."""

    _SLUGS: ClassVar[tuple[str, ...]] = (
        "introduction", "core-concepts", "hands-on-practice",
    )

    _EXPECTED_TERMS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "Active Directory Domain Services", "AD DS", "Domain Controller",
            "domain", "directory service", "object", "attribute",
            "user", "group", "computer account", "Organizational Unit",
            "OU is not a security boundary", "DNS", "service location",
            "NetBIOS", "YUSHA.LOCAL", "Illustrative example",
        ],
        "core-concepts": [
            "Authentication", "Authorization", "Kerberos", "KDC",
            "Key Distribution Center", "Authentication Service",
            "Ticket Granting Service", "TGT", "Ticket Granting Ticket",
            "service ticket", "AS-REQ", "TGS-REQ", "NTLM",
            "LDAP", "Lightweight Directory Access Protocol",
            "Group Policy", "GPO", "Computer Configuration",
            "User Configuration", "ACL", "Access Control Entries",
            "security principal", "SID", "Forest", "Trust",
            "least privilege", "delegation", "Illustrative example",
        ],
        "hands-on-practice": [
            "OBSERVATION", "EVIDENCE", "INTERPRETATION",
            "SECURITY IMPACT", "RECOMMENDATION", "CONFIDENCE",
            "AD COMPONENT", "SECURITY RELEVANCE", "POTENTIAL IMPACT",
            "RECOMMENDED CONTROL",
            "read-only investigation", "effective access",
        ],
    }

    # The exact WRONG/CORRECT corrections the driving spec named.
    _REQUIRED_CORRECTIONS: ClassVar[dict[str, list[str]]] = {
        "introduction": [
            "Active Directory is just a database of usernames and passwords.",
            "Domain Controller = Active Directory.",
            "An OU is a security boundary.",
            "Active Directory is DNS.",
        ],
        "core-concepts": [
            "Kerberos sends the user's password to every service.",
            "LDAP is the authentication protocol.",
            "Being authenticated means you can access the resource.",
            "An OU is a security boundary.",
            "Group Policy is only cosmetic.",
            "NTLM is always insecure and nobody uses it.",
            "Every Windows domain uses only one authentication protocol.",
            "OU = GPO.",
        ],
    }

    @staticmethod
    def _render(app, slug):
        from app.roadmap.content_render import render_lesson_content
        with app.app_context():
            return render_lesson_content(
                f"roadmap/intermediate/active-directory-basics/{slug}.md"
            )

    @staticmethod
    def _raw_lesson(slug):
        from pathlib import Path

        import app as app_pkg
        path = (Path(app_pkg.__file__).parent / "content" / "roadmap"
                / "intermediate" / "active-directory-basics" / f"{slug}.md")
        return path.read_text(encoding="utf-8")

    def test_all_three_lessons_render_real_content(self, app):
        for slug in self._SLUGS:
            html = self._render(app, slug)
            assert html is not None, f"{slug}: content file missing or unreadable"
            assert "coming soon" not in html.lower()
            assert len(html) > 3000, f"{slug}: suspiciously short ({len(html)} chars)"

    def test_lessons_contain_their_taught_terms(self, app):
        for slug, terms in self._EXPECTED_TERMS.items():
            html = self._render(app, slug)
            for term in terms:
                assert term in html, f"{slug}: missing expected term {term!r}"

    def test_lessons_keep_their_misconception_corrections(self, app):
        for slug, claims in self._REQUIRED_CORRECTIONS.items():
            html = self._render(app, slug)
            for claim in claims:
                assert claim in html, f"{slug}: lost required correction {claim!r}"

    def test_lessons_contain_real_code_examples(self, app):
        for slug in self._SLUGS:
            html = self._render(app, slug)
            assert "<pre>" in html and "<code>" in html, f"{slug}: no code block rendered"

    def test_no_placeholder_language_anywhere_in_lessons(self, app):
        banned = ("coming soon", "lorem ipsum", "todo", "check back soon",
                  "content is being written", "placeholder content",
                  "placeholder text", "this is a placeholder",
                  "to be written", "tbd")
        for slug in self._SLUGS:
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: contains banned phrase {phrase!r}"

    # ── The terminology distinctions this module exists to install ────
    def test_ad_ad_ds_and_domain_controller_are_kept_distinct(self, app):
        """The single most important vocabulary split in the module."""
        intro = self._render(app, "introduction")
        assert "Three Words That Are Not Synonyms" in intro
        assert ("<strong>AD DS is the service. A Domain Controller is a server "
                "that runs it. Active Directory is the family name.</strong>") in intro
        assert "Domain ≠ Domain Controller." in intro

    def test_domain_controller_taught_as_more_than_a_password_store(self, app):
        """The spec forbids reducing a DC to 'the server where passwords
        are stored' — six named jobs must survive."""
        intro = self._render(app, "introduction")
        assert "What a Domain Controller Actually Does" in intro
        for job in ("Hosts AD DS", "Authenticates domain identities",
                    "Runs the KDC", "Serves directory queries",
                    "Stores and distributes policy",
                    "Participates in domain security decisions"):
            assert job in intro, f"introduction: DC job {job!r} missing"

    def test_dns_dependency_is_taught_without_conflating_the_two(self, app):
        intro = self._render(app, "introduction")
        assert "DNS and Active Directory" in intro
        assert "service location" in intro
        assert "Active Directory <em>depends</em> on DNS" in intro

    def test_ou_is_not_a_security_boundary_in_two_lessons(self, app):
        """Stated in Introduction and demonstrated in Core Concepts'
        boundary table — losing either weakens the module's clearest
        structural correction."""
        intro = self._render(app, "introduction")
        assert "not</strong> an inherent security boundary" in intro
        core = self._render(app, "core-concepts")
        assert "What Is Actually a Boundary" in core
        hands = self._render(app, "hands-on-practice")
        assert "an OU is not a security boundary" in hands

    def test_group_based_authorization_chain_is_taught(self, app):
        intro = self._render(app, "introduction")
        assert "Why Access Goes Through Them" in intro
        core = self._render(app, "core-concepts")
        assert "<strong>most permissive one wins</strong>" in core
        assert "allow permissions from multiple groups" in core

    def test_kerberos_ticket_model_is_taught_correctly(self, app):
        core = self._render(app, "core-concepts")
        for term in ("Authentication Service", "Ticket Granting Service",
                     "TGT", "service ticket", "KDC"):
            assert term in core, f"core-concepts: Kerberos term {term!r} missing"
        # The TGT/service-ticket distinction, stated as a correction.
        assert "The TGT is what gets you into the file server." in core
        assert "It is presented to the KDC, not to services." in core

    def test_ldap_and_kerberos_roles_are_separated(self, app):
        core = self._render(app, "core-concepts")
        assert ("LDAP is a <strong>directory access</strong> protocol") in core
        assert "directory access" in core
        assert "Kerberos is the primary" in core

    def test_ntlm_taught_as_legacy_not_as_absent(self, app):
        """The spec explicitly forbids 'NTLM is always insecure and never
        used'. Both halves — why it persists and why it concerns — must
        be present."""
        core = self._render(app, "core-concepts")
        assert "Why it still exists." in core
        assert "Why it is a concern." in core
        assert "This platform does not simulate NTLM." in self._raw_lesson(
            "core-concepts")

    def test_gpo_and_ou_relationship_is_taught_precisely(self, app):
        core = self._render(app, "core-concepts")
        assert "GPOs and OUs — the Actual Relationship" in core
        assert "A GPO can be <strong>linked</strong> to a scope" in core
        assert "Computer Configuration" in core and "User Configuration" in core

    def test_authentication_versus_authorization_is_taught(self, app):
        core = self._render(app, "core-concepts")
        assert "Authentication Is Not Authorization" in core
        assert ("the Domain Controller proves identity; the file server "
                "decides access") in core

    def test_security_principles_section_exists(self, app):
        core = self._render(app, "core-concepts")
        assert "Security Principles for Active Directory" in core
        for principle in ("Least privilege", "Group-based access",
                          "Separation of administrative roles",
                          "Strong authentication", "Controlled delegation",
                          "Auditing", "Patch management",
                          "Secure configuration"):
            assert principle in core, f"core-concepts: principle {principle!r} missing"

    def test_hands_on_has_investigation_exercises_and_report(self, app):
        hands = self._render(app, "hands-on-practice")
        for heading in ("Exercise 1 — The Domain and Its Controller",
                        "Exercise 2 — The User Population",
                        "Exercise 3 — Groups and Where Privilege Actually Lives",
                        "Exercise 4 — Structure: OUs and Computers",
                        "Exercise 5 — Shares, ACLs and Effective Access",
                        "Exercise 6 — Group Policy",
                        "Exercise 7 — Watching Kerberos",
                        "Exercise 8 — The Investigation Report"):
            assert heading in hands, f"hands-on-practice: {heading!r} missing"
        for field in ("OBSERVATION:", "EVIDENCE:", "AD COMPONENT:",
                      "SECURITY RELEVANCE:", "POTENTIAL IMPACT:",
                      "RECOMMENDED CONTROL:", "CONFIDENCE:"):
            assert field in hands, f"hands-on-practice: report field {field!r} missing"

    # ── Safety ────────────────────────────────────────────────────────
    def test_no_offensive_or_unauthorized_framing(self, app):
        """Permanent safety rule: this module teaches AD as a system, from
        an administrator's and assessor's chair. It must never drift into
        credential attacks, ticket abuse or privilege escalation — that
        material belongs to later, gated modules."""
        banned = ("kerberoast", "pass-the-hash", "pass the hash",
                  "pass-the-ticket", "golden ticket", "silver ticket",
                  "dcsync", "dump the ntds", "ntds.dit", "mimikatz",
                  "crack the password", "brute-force the domain",
                  "any real domain", "your employer's domain")
        for slug in self._SLUGS:
            html = self._render(app, slug).lower()
            for phrase in banned:
                assert phrase not in html, f"{slug}: unsafe framing {phrase!r}"

    def test_authorization_boundary_is_stated(self, app):
        intro = self._render(app, "introduction")
        assert "Authorization and Scope" in intro
        assert "written permission" in intro
        hands = self._render(app, "hands-on-practice")
        assert "Authorization Comes First" in hands
        assert "read-only investigation" in hands
        core = self._render(app, "core-concepts")
        for html, slug in ((intro, "introduction"), (core, "core-concepts"),
                           (hands, "hands-on-practice")):
            assert "authoriz" in html.lower(), f"{slug}: no authorization framing"

    def test_no_real_credentials_are_printed(self, app):
        """Every account named is a fictional simulator object, and the
        simulator stores no passwords at all — asserted rather than
        assumed, so a future domain definition carrying credentials would
        fail here before it reached a lesson."""
        from app.labs.ad import domains

        definition = domains.BUILTIN_DOMAINS["yusha-local"]
        for user in definition["users"]:
            assert "password" not in user, (
                f"{user['sam']}: domain definition carries a password field"
            )
        intro = self._render(app, "introduction")
        assert "Never put real credentials" in intro

    # ── Honesty: what this platform cannot demonstrate ────────────────
    def test_unsimulated_topics_are_labelled_illustrative(self, app):
        """LDAP, AD's DNS service records, NTLM, forests and trusts have
        no simulator behind them. Each must say so rather than implying
        the example came from a running system."""
        intro = self._raw_lesson("introduction")
        core = self._raw_lesson("core-concepts")
        assert "**Illustrative example — not captured output.**" in intro, "DNS"
        assert ("does not model AD service records, so there is nothing real "
                "to quote here") in intro
        assert ("**Illustrative example — not captured output. This platform "
                "has no LDAP simulator**") in core
        assert "This platform does not simulate NTLM." in core
        assert ("**This platform simulates a single domain, `YUSHA.LOCAL`.**"
                in core), "forest/trust"

    def test_absence_of_an_ad_mission_is_real(self, app):
        """hands-on §13 states outright that no AD terminal mission
        exists, which is why no mission link is offered. If one is ever
        added, that honesty note becomes wrong — fail here first."""
        from app.core.missions.mission_loader import MISSIONS

        for slug, mission in MISSIONS.items():
            haystack = (slug + " " + mission.get("title", "") + " "
                        + mission.get("category", "")).lower()
            for token in ("active directory", "domain controller", "kerberos",
                          "ldap"):
                assert token not in haystack, (
                    f"mission {slug!r} now looks AD-related — hands-on §13 "
                    f"says none exists"
                )
        raw = self._raw_lesson("hands-on-practice")
        assert ("There is no Active Directory terminal mission on this "
                "platform.") in raw
        assert len(MISSIONS) == 16

    # ── Structure untouched ───────────────────────────────────────────
    def test_lessons_not_flagged_empty_or_placeholder_by_audit(self, app):
        from app.roadmap.audit import _lesson_content_state
        from app.roadmap.models import Lesson, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(
                slug="active-directory-basics").first()
            lessons = Lesson.query.filter_by(module_id=module.id).all()
            assert len(lessons) == 3
            for lesson in lessons:
                is_empty, is_placeholder = _lesson_content_state(lesson)
                assert not is_empty, f"{lesson.slug}: flagged empty"
                assert not is_placeholder, f"{lesson.slug}: flagged placeholder"

    def test_lesson_ids_and_order_unchanged_by_content_edit(self, app):
        """Writing real content must never touch the locked structure —
        same 3 lesson slugs, same display_order, same XP as YC-036.2, and
        the module still sits at Intermediate display_order 5."""
        from app.roadmap.models import Lesson, RoadmapCategory, RoadmapModule

        with app.app_context():
            module = RoadmapModule.query.filter_by(
                slug="active-directory-basics").first()
            assert module.id == 13
            assert module.display_order == 5
            intermediate = RoadmapCategory.query.filter_by(
                title="Intermediate").first()
            assert module.category_id == intermediate.id
            assert module.difficulty == "intermediate"
            assert module.estimated_hours == 1
            assert module.xp_reward == 175
            lessons = (
                Lesson.query.filter_by(module_id=module.id)
                .order_by(Lesson.display_order).all()
            )
            assert [lesson.id for lesson in lessons] == [37, 38, 39]
            assert [lesson.slug for lesson in lessons] == [
                "introduction", "core-concepts", "hands-on-practice",
            ]
            assert [lesson.display_order for lesson in lessons] == [1, 2, 3]
            assert [lesson.xp_reward for lesson in lessons] == [25, 50, 100]
            assert [lesson.estimated_minutes for lesson in lessons] == [10, 20, 30]
            assert [lesson.content_path for lesson in lessons] == [
                "roadmap/intermediate/active-directory-basics/introduction.md",
                "roadmap/intermediate/active-directory-basics/core-concepts.md",
                "roadmap/intermediate/active-directory-basics/hands-on-practice.md",
            ]
            assert lessons[0].is_preview is True
            assert lessons[1].is_preview is False
            assert lessons[2].is_preview is False

    def test_intermediate_module_order_unchanged(self, app):
        """Nmap < Wireshark < Burp Suite < OWASP Top 10 < AD Basics."""
        from app.roadmap.models import RoadmapCategory, RoadmapModule

        with app.app_context():
            intermediate = RoadmapCategory.query.filter_by(
                title="Intermediate").first()
            order = [
                (m.slug, m.display_order) for m in
                RoadmapModule.query.filter_by(category_id=intermediate.id)
                .order_by(RoadmapModule.display_order).limit(6).all()
            ]
            assert order == [("nmap", 1), ("wireshark", 2), ("burp-suite", 3),
                             ("owasp-top-10", 4),
                             ("active-directory-basics", 5),
                             ("metasploit", 6)]

    # ── Practice links ────────────────────────────────────────────────
    def test_practice_links_are_scoped_and_no_terminal_or_mission_link(
            self, app, student):
        """introduction has no practice CTA; core-concepts and
        hands-on-practice both link the AD orientation lab. No lesson
        offers a mission (none exists) or the free-practice terminal."""
        from app.auth.models import User
        from app.roadmap.services import get_lesson_view_context

        _uname, uid = student
        expected = {"introduction": False, "core-concepts": True,
                    "hands-on-practice": True}
        with app.app_context():
            student_user = User.query.get(uid)
            for slug, want_lab in expected.items():
                ctx = get_lesson_view_context(
                    student_user, "active-directory-basics", slug)
                assert ctx is not None
                practice = ctx["practice"]
                assert not practice.get("show_terminal"), slug
                assert practice.get("mission_slug") is None, slug
                assert bool(practice.get("lab_slug")) is want_lab, slug
                if want_lab:
                    assert practice["lab_slug"] == "ad-orientation"
                    assert practice["lab_title"] == "AD Basics: Explore YUSHA.LOCAL"

    def test_free_practice_terminal_has_no_ad_commands(self, app):
        """The reason `active-directory-basics` is excluded from
        _TERMINAL_PRACTICE_MODULES: the shell's command registry has no
        AD verb at all, so a free-practice CTA would send students
        somewhere nothing in this module works."""
        from app.core.terminal.shell import Shell

        sh = Shell()
        for verb in ("get-users", "get-groups", "get-ous", "get-computers",
                     "kerberos", "gpos", "policy"):
            out = sh.execute(verb)
            assert "not found" in out.lower() or "not recognized" in out.lower(), (
                f"{verb!r} unexpectedly exists in the free-practice terminal: "
                f"{out!r}"
            )

    def test_lab_link_points_to_a_real_reachable_ungated_lab(self, app):
        with app.test_request_context():
            from flask import url_for
            assert url_for("labs.detail", slug="ad-orientation") == (
                "/labs/ad-orientation"
            )
        with app.app_context():
            from app.labs.models import Lab
            lab = Lab.query.filter_by(slug="ad-orientation").first()
            assert lab is not None and lab.is_active and lab.is_interactive
            assert lab.title == "AD Basics: Explore YUSHA.LOCAL"
            assert lab.prerequisite_lab_id is None
            assert lab.simulator_key == "ad"

    def test_ad_lab_chain_named_in_lesson_is_real_and_really_gated(self, app):
        """hands-on §13 names all five AD labs and states they unlock in
        order. Both halves verified: they exist with those titles, and the
        chain really is linear with ad-orientation as its only entry."""
        raw = self._raw_lesson("hands-on-practice")
        chain = ["ad-orientation", "ad-inactive-account",
                 "ad-compromised-password", "ad-overprivileged",
                 "ad-least-privilege"]
        with app.app_context():
            from app.labs.models import Lab
            previous = None
            for slug in chain:
                lab = Lab.query.filter_by(slug=slug).first()
                assert lab is not None and lab.is_active, f"{slug}: not a real lab"
                assert lab.title in raw, (
                    f"{slug}: lesson names a title the database does not have "
                    f"({lab.title!r})"
                )
                if previous is None:
                    assert lab.prerequisite_lab_id is None
                else:
                    assert lab.prerequisite_lab_id == previous.id, (
                        f"{slug}: chain order drifted from the lesson's claim"
                    )
                previous = lab

    def test_orientation_lab_objectives_match_the_lesson_exercises(self, app):
        """hands-on §13 claims the lab's six objectives map onto this
        module's material. Verified against the real objective rows."""
        with app.app_context():
            from app.labs.models import Lab, LabObjective
            lab = Lab.query.filter_by(slug="ad-orientation").first()
            objectives = LabObjective.query.filter_by(lab_id=lab.id).all()
            assert len(objectives) == 6, (
                f"lesson says six scored objectives, found {len(objectives)}"
            )

    # ── Real-evidence guard ────────────────────────────────────────────
    _I: ClassVar[str] = "introduction"
    _C: ClassVar[str] = "core-concepts"
    _H: ClassVar[str] = "hands-on-practice"

    def _steps(self):
        """Every console command a lesson quotes, replayed in order on one
        simulator session. Each entry is (command, lesson-slug or tuple of
        slugs, or None for a step no lesson quotes)."""
        i, c, h = self._I, self._C, self._H
        return [
            ("help", h),
            ("whoami", h),
            ("hostname", h),
            ("get-computers", (i, h)),
            ("get-computer DC-01", (i, h)),
            ("get-ous", (i, h)),
            ("get-ou IT", h),
            ("get-ou Interns", h),
            ("get-users", h),
            ("get-user skhadka", i),
            ("get-user kshrestha", (i, h)),
            ("get-user mrai", (i, h)),
            ("get-user svc-backup", h),
            ("get-user intern01", h),
            ("get-groups", (i, h)),
            ('get-group "Domain Admins"', h),
            ("members help-desk", h),
            ("get-shares", h),
            ("get-share HR-Confidential", (c, h)),
            ("gpos", (c, h)),
            ("policy", (c, h)),
            ("access mrai HR-Confidential", (c, h)),
            ("access lbasnet HR-Confidential", (c, h)),
            ("access dtamang HR-Confidential", (c, h)),
            ("access intern01 HR-Confidential", (c, h)),
            ("access dtamang Finance-Reports", h),
            ("access skhadka Finance-Reports", (c, h)),
            ("reset-password dtamang short", c),
            ("kerberos skhadka", (c, h)),
            ("kerberos mrai", (c, h)),
        ]

    @staticmethod
    def _simulator():
        """A session on the same domain the real AD orientation lab
        loads (`ad-orientation` -> YUSHA.LOCAL, app/labs/ad/domains.py)."""
        from app.labs.ad.simulator import ADSimulator

        class _Lab:
            slug = "ad-orientation"

        sim = ADSimulator()
        return sim, sim.bootstrap(_Lab(), {})

    def test_quoted_console_output_matches_the_real_simulator(self, app):
        """Every directory listing, object inspection, GPO, policy, access
        check and Kerberos flow quoted in all three lessons was captured by
        actually running this platform's real AD simulator against the real
        YUSHA.LOCAL domain definition. If the simulator's data or output
        formatting ever changes, the lessons become fabricated evidence —
        fail here rather than ship a lie."""
        from app.labs.simulator_base import Action

        raws = {slug: self._raw_lesson(slug) for slug in self._SLUGS}
        sim, state = self._simulator()
        for index, (command, slugs) in enumerate(self._steps()):
            result = sim.handle(
                state, Action(type="command", payload={"command": command}))
            state = result.new_state
            if slugs is None:
                continue
            if isinstance(slugs, str):
                slugs = (slugs,)
            for line in result.output.splitlines():
                line = line.strip()
                if not line:
                    continue
                for slug in slugs:
                    assert line in raws[slug], (
                        f"{slug}: quoted output no longer matches the real AD "
                        f"simulator for `{command}` (step {index}) — {line!r}"
                    )

    def test_quoted_welcome_screen_matches_the_real_simulator(self, app):
        """hands-on §2 prints the console's real welcome screen, including
        the object counts — which are derived from the domain definition,
        so they drift the moment the domain changes."""
        raw = self._raw_lesson("hands-on-practice")
        sim, state = self._simulator()
        for line in sim.welcome(state).splitlines():
            line = line.strip()
            if line:
                assert line in raw, f"welcome screen drifted — {line!r}"

    def test_domain_facts_the_lessons_rest_on_are_real(self, app):
        """Three findings drive the entire hands-on lesson. Each is
        asserted against the domain definition, not merely quoted: if the
        training domain is ever cleaned up, the lessons become fiction."""
        from app.labs.ad import domains

        definition = domains.BUILTIN_DOMAINS["yusha-local"]
        assert definition["name"] == "YUSHA.LOCAL"
        assert definition["netbios"] == "YUSHA"

        users = {u["sam"]: u for u in definition["users"]}
        # Finding 1 — the over-privileged intern.
        assert "domain-admins" in users["intern01"]["groups"]
        assert users["intern01"]["ou"] == "interns"
        # Finding 2 — the dormant account.
        assert users["kshrestha"]["last_logon_days"] == 210
        assert users["kshrestha"]["enabled"] is True
        # Finding 3 — the locked-out account and its failed-attempt count.
        assert users["mrai"]["locked"] is True
        assert users["mrai"]["failed_attempts"] == 14

        # Finding 4 — the domain-wide ACE on the confidential share.
        hr_share = next(s for s in definition["shares"]
                        if s["slug"] == "hr-confidential")
        acl = {entry["group"]: entry["right"] for entry in hr_share["acl"]}
        assert acl["domain-users"] == "read", (
            "the HR share's domain-wide READ entry is the lesson's central "
            "audit finding"
        )
        # The control case that proves it is an anomaly, not the pattern.
        finance = next(s for s in definition["shares"]
                       if s["slug"] == "finance-reports")
        assert "domain-users" not in {e["group"] for e in finance["acl"]}

        # The password/lockout policy Core Concepts §10 and Exercise 6 quote.
        gpo = next(g for g in definition["gpos"]
                   if g["slug"] == "default-domain-policy")
        assert gpo["password_policy"]["min_length"] == 12
        assert gpo["lockout_policy"]["threshold"] == 5

    def test_locked_account_really_fails_authentication_before_the_acl(self, app):
        """Core Concepts §2 and Exercise 7 both rest on authentication
        being evaluated before authorization — asserted, not assumed."""
        from app.labs.simulator_base import Action

        sim, state = self._simulator()
        result = sim.handle(state, Action(
            type="command",
            payload={"command": "access mrai HR-Confidential"}))
        assert "ACCESS DENIED" in result.output
        assert "cannot authenticate" in result.output
        assert "whatever the ACL says" in result.output

    def test_password_policy_really_rejects_a_weak_password(self, app):
        """Core Concepts §10 shows the GPO enforcing itself against an
        administrator. If enforcement is ever removed, the lesson's
        'policy with teeth' claim becomes false."""
        from app.labs.simulator_base import Action

        sim, state = self._simulator()
        result = sim.handle(state, Action(
            type="command",
            payload={"command": "reset-password dtamang short"}))
        assert "REJECTED by policy" in result.output
        assert "at least 12 characters" in result.output

    # ── Rendering, XP and progression ─────────────────────────────────
    def test_lesson_pages_render_over_http_once_unlocked(self, app, student):
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(
                slug="active-directory-basics").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug in self._SLUGS:
                r = c.get(f"/roadmap/active-directory-basics/{slug}/")
                assert r.status_code == 200, slug
                body = r.data.decode("utf-8")
                assert "coming soon" not in body.lower(), slug

    def test_cybermentor_context_is_set_on_every_lesson_page(self, app, student):
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(
                slug="active-directory-basics").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()

        with app.test_client() as c:
            _login(c, uname)
            for slug, title in (("introduction", "Introduction"),
                                ("core-concepts", "Core Concepts"),
                                ("hands-on-practice", "Hands-on Practice")):
                r = c.get(f"/roadmap/active-directory-basics/{slug}/")
                body = r.data.decode("utf-8")
                assert (f'data-mentor-lab="Active Directory Basics — {title}"'
                        in body)

    def test_completion_awards_xp_exactly_once(self, app, student):
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress

        uname, uid = student
        with app.app_context():
            module = RoadmapModule.query.filter_by(
                slug="active-directory-basics").first()
            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            if row is None:
                row = UserModuleProgress(user_id=uid, module_id=module.id)
                db.session.add(row)
            row.unlocked = True
            db.session.commit()
            before = User.query.get(uid).xp

        with app.test_client() as c:
            _login(c, uname)
            c.post("/roadmap/active-directory-basics/core-concepts/complete",
                   follow_redirects=True)
            with app.app_context():
                after_first = User.query.get(uid).xp
            c.post("/roadmap/active-directory-basics/core-concepts/complete",
                   follow_redirects=True)
            with app.app_context():
                after_second = User.query.get(uid).xp

        assert after_first == before + 50, "core-concepts should award exactly 50 XP"
        assert after_second == after_first, "XP awarded twice for one lesson"

    def test_module_completion_awards_bonus_and_unlocks_metasploit(self, app):
        """A dedicated user completes all three AD lessons: 25 + 50 + 100
        lesson XP + 175 module bonus = 350, awarded once, and
        `metasploit` (Intermediate #6) becomes available."""
        from app.auth.models import User
        from app.extensions import db
        from app.roadmap.models import RoadmapModule, UserModuleProgress
        from app.roadmap.services import complete_lesson, module_status

        with app.app_context():
            u = User(username="ad_module_complete", email="ad_complete@t.io")
            u.set_password("Str0ngPass!")
            db.session.add(u)
            db.session.commit()
            uid = u.id

            module = RoadmapModule.query.filter_by(
                slug="active-directory-basics").first()
            db.session.add(UserModuleProgress(
                user_id=uid, module_id=module.id, unlocked=True))
            db.session.commit()

            before = User.query.get(uid).xp
            for slug in self._SLUGS:
                complete_lesson(User.query.get(uid),
                                "active-directory-basics", slug)
            after = User.query.get(uid).xp
            assert after == before + 350

            for slug in self._SLUGS:
                result = complete_lesson(User.query.get(uid),
                                         "active-directory-basics", slug)
                assert result["already_completed"] is True
                assert result["xp_awarded"] == 0
            assert User.query.get(uid).xp == after

            row = UserModuleProgress.query.filter_by(
                user_id=uid, module_id=module.id).first()
            assert row.completed is True
            assert row.bonus_awarded is True

            nxt = RoadmapModule.query.filter_by(slug="metasploit").first()
            assert module_status(User.query.get(uid), nxt) == "available"


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
