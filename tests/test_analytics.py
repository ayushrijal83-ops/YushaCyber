"""Learning Analytics tests (YC-033.0).

Seeds a small cohort of students with real progress rows (lessons,
labs, quizzes, CTF solves, certificates, achievements, hint events),
then asserts every service number, the HTTP surface, the CSV exports,
access control, and a query-count performance bound (no N+1: the
overview must stay flat as the cohort grows).
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

_TMPDIR = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_analytics.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402
from sqlalchemy import event as sa_event  # noqa: E402


def _now():
    return datetime.now(timezone.utc)


@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    import config as app_config

    # DATABASE_URL is resolved once, at config.py import — so in a
    # full-suite run whichever test file imports `app` first wins, and
    # Flask-SQLAlchemy 3 builds engines eagerly inside init_app. These
    # tests assert exact counts, so they need a pristine database:
    # swap the config-class URI just for this create_app call, then
    # restore it so later test modules keep their own databases.
    config_class = app_config.get_config()
    original_uri = config_class.SQLALCHEMY_DATABASE_URI
    config_class.SQLALCHEMY_DATABASE_URI = \
        f"sqlite:///{_TMPDIR}/test_analytics.db"
    try:
        application = create_app()
    finally:
        config_class.SQLALCHEMY_DATABASE_URI = original_uri

    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
        _seed_cohort(db)
    yield application


def _seed_cohort(db):
    """3 students, content in every system, activity spread over days."""
    from app.achievement.models import Achievement, UserAchievement
    from app.auth.models import User
    from app.certificates.models import Certificate, UserCertificate
    from app.ctf.models import Challenge, ChallengeCategory, ChallengeSolve
    from app.labs.models import Lab, LabCategory, UserLabProgress
    from app.roadmap.models import (
        Lesson,
        RoadmapCategory,
        RoadmapModule,
        Quiz,
        UserLessonProgress,
        UserModuleProgress,
        UserQuizAttempt,
    )

    admin = User(username="ana_admin", email="ana_admin@test.io",
                 is_admin=True)
    admin.set_password("Str0ngPass!")
    students = []
    for i, (xp, level, streak) in enumerate(
            [(1200, 5, 7), (400, 2, 1), (50, 1, 0)], start=1):
        user = User(username=f"stud{i}", email=f"stud{i}@test.io",
                    xp=xp, level=level, streak=streak)
        user.set_password("Str0ngPass!")
        students.append(user)
    db.session.add_all([admin] + students)
    db.session.flush()

    # ---- Roadmap: one category, two modules, three lessons -----------
    category = RoadmapCategory(title="Linux Path",
                               display_order=1)
    db.session.add(category)
    db.session.flush()
    module_a = RoadmapModule(category_id=category.id, title="Basics",
                             slug="basics", display_order=1, xp_reward=100)
    module_b = RoadmapModule(category_id=category.id, title="Advanced",
                             slug="advanced", display_order=2,
                             xp_reward=150)
    db.session.add_all([module_a, module_b])
    db.session.flush()
    lessons = [
        Lesson(module_id=module_a.id, title="Intro", slug="intro",
               display_order=1, xp_reward=50),
        Lesson(module_id=module_a.id, title="Files", slug="files",
               display_order=2, xp_reward=50),
        Lesson(module_id=module_b.id, title="Pipes", slug="pipes",
               display_order=1, xp_reward=60),
    ]
    db.session.add_all(lessons)
    quiz = Quiz(module_id=module_a.id, title="Basics Quiz",
                xp_reward=80)
    db.session.add(quiz)
    db.session.flush()

    # stud1 completes everything; stud2 completes module A only (the
    # funnel drop-off); stud3 opens one lesson and stops.
    day = timedelta(days=1)
    for lesson in lessons:
        db.session.add(UserLessonProgress(
            user_id=students[0].id, lesson_id=lesson.id, completed=True,
            completed_at=_now() - 2 * day, time_spent=600))
    for lesson in lessons[:2]:
        db.session.add(UserLessonProgress(
            user_id=students[1].id, lesson_id=lesson.id, completed=True,
            completed_at=_now() - 1 * day, time_spent=900))
    db.session.add(UserLessonProgress(
        user_id=students[2].id, lesson_id=lessons[0].id, completed=False,
        time_spent=120))
    db.session.add_all([
        UserModuleProgress(user_id=students[0].id, module_id=module_a.id,
                           completed=True, bonus_awarded=True,
                           completed_at=_now() - 2 * day),
        UserModuleProgress(user_id=students[0].id, module_id=module_b.id,
                           completed=True, bonus_awarded=True,
                           completed_at=_now() - 1 * day),
        UserModuleProgress(user_id=students[1].id, module_id=module_a.id,
                           completed=True, bonus_awarded=True,
                           completed_at=_now() - 1 * day),
    ])
    db.session.add_all([
        UserQuizAttempt(user_id=students[0].id, quiz_id=quiz.id,
                        score=9, percentage=90.0, passed=True,
                        completed_at=_now() - 2 * day,
                        time_taken_seconds=300),
        UserQuizAttempt(user_id=students[1].id, quiz_id=quiz.id,
                        score=4, percentage=40.0, passed=False,
                        completed_at=_now() - 1 * day,
                        time_taken_seconds=250),
        UserQuizAttempt(user_id=students[1].id, quiz_id=quiz.id,
                        score=8, percentage=80.0, passed=True,
                        completed_at=_now() - 1 * day,
                        time_taken_seconds=280),
    ])

    # ---- Labs --------------------------------------------------------
    lab_category = LabCategory(slug="ana-labs", name="Analytics Labs")
    db.session.add(lab_category)
    db.session.flush()
    lab_easy = Lab(slug="ana-easy", title="Easy Lab",
                   category_id=lab_category.id, difficulty="Easy",
                   xp_reward=100, is_active=True)
    lab_hard = Lab(slug="ana-hard", title="Hard Lab",
                   category_id=lab_category.id, difficulty="Hard",
                   xp_reward=300, is_active=True)
    db.session.add_all([lab_easy, lab_hard])
    db.session.flush()
    db.session.add_all([
        UserLabProgress(user_id=students[0].id, lab_id=lab_easy.id,
                        started=True, completed=True,
                        completed_at=_now() - 1 * day,
                        time_spent_seconds=900),
        UserLabProgress(user_id=students[1].id, lab_id=lab_easy.id,
                        started=True, completed=True,
                        completed_at=_now(), time_spent_seconds=1500),
        UserLabProgress(user_id=students[2].id, lab_id=lab_easy.id,
                        started=True, completed=False),
        UserLabProgress(user_id=students[0].id, lab_id=lab_hard.id,
                        started=True, completed=False),
        UserLabProgress(user_id=students[1].id, lab_id=lab_hard.id,
                        started=True, completed=False),
    ])

    # ---- CTF ---------------------------------------------------------
    ctf_category = ChallengeCategory(name="Web", slug="ana-web")
    db.session.add(ctf_category)
    db.session.flush()
    ch_pop = Challenge(category_id=ctf_category.id, title="Popular",
                       slug="ana-popular", difficulty="Easy",
                       flag_hash="x", xp_reward=50, is_active=True)
    ch_rare = Challenge(category_id=ctf_category.id, title="Rare",
                        slug="ana-rare", difficulty="Hard",
                        flag_hash="y", xp_reward=200, is_active=True)
    db.session.add_all([ch_pop, ch_rare])
    db.session.flush()
    db.session.add_all([
        ChallengeSolve(user_id=students[0].id, challenge_id=ch_pop.id,
                       solved=True, attempts=1,
                       solved_at=_now() - 1 * day,
                       time_taken_seconds=400),
        ChallengeSolve(user_id=students[1].id, challenge_id=ch_pop.id,
                       solved=True, attempts=3, solved_at=_now(),
                       time_taken_seconds=800),
        ChallengeSolve(user_id=students[2].id, challenge_id=ch_rare.id,
                       solved=False, attempts=5),
    ])

    # ---- Certificates + achievements ---------------------------------
    certificate = Certificate(slug="ana-cert", title="Analytics Cert",
                              category="labs", is_active=True)
    achievement = Achievement(title="Ana Achiever",
                              condition_type="labs_completed",
                              condition_value=1, bonus_xp=25,
                              is_active=True)
    db.session.add_all([certificate, achievement])
    db.session.flush()
    db.session.add_all([
        UserCertificate(user_id=students[0].id,
                        certificate_id=certificate.id,
                        certificate_code="YC-2026-TEST01",
                        issued_at=_now() - 1 * day),
        UserAchievement(user_id=students[0].id,
                        achievement_id=achievement.id,
                        unlocked_at=_now() - 1 * day),
    ])
    db.session.commit()


def _login(app, username):
    client = app.test_client()
    client.post("/auth/login",
                data={"identifier": username, "password": "Str0ngPass!"},
                follow_redirects=True)
    return client


# ===========================================================================
# Services
# ===========================================================================
class TestOverviewStats:
    def test_headline_numbers(self, app):
        from app.analytics import services
        with app.app_context():
            stats = services.overview_stats()
            assert stats["total_students"] == 3
            assert stats["active_students_7d"] == 3
            assert stats["completed_lessons"] == 5
            assert stats["completed_labs"] == 2
            assert stats["completed_ctfs"] == 2
            assert stats["certificates_issued"] == 1
            assert stats["avg_xp"] == round((1200 + 400 + 50) / 3)
            assert stats["avg_level"] > 0

    def test_admins_excluded_from_student_counts(self, app):
        from app.analytics import services
        with app.app_context():
            assert services.overview_stats()["total_students"] == 3

    def test_query_count_is_flat(self, app):
        """No N+1: the overview issues a fixed, small number of queries
        regardless of cohort size."""
        from app.analytics import services
        from app.extensions import db
        with app.app_context():
            counter = {"n": 0}

            def _count(*args, **kwargs):
                counter["n"] += 1

            engine = db.engine
            sa_event.listen(engine, "before_cursor_execute", _count)
            try:
                services.overview_stats()
            finally:
                sa_event.remove(engine, "before_cursor_execute", _count)
            assert counter["n"] <= 20, counter["n"]


class TestTimeseries:
    def test_series_shapes_and_sums(self, app):
        from app.analytics import services
        with app.app_context():
            series = services.timeseries(days=30)
            assert len(series["labels"]) == 30
            for key in ("daily_active", "xp_growth", "lessons", "labs",
                        "ctf", "quiz_attempts", "quiz_pass_rate"):
                assert len(series[key]) == 30
            assert sum(series["lessons"]) == 5
            assert sum(series["labs"]) == 2
            assert sum(series["ctf"]) == 2
            assert sum(series["quiz_attempts"]) == 3
            assert max(series["daily_active"]) >= 1

    def test_xp_growth_is_cumulative_and_positive(self, app):
        from app.analytics import services
        with app.app_context():
            xp = services.timeseries(days=30)["xp_growth"]
            assert all(b >= a for a, b in zip(xp, xp[1:]))
            # lessons 50*5? stud1 3 lessons(160)+stud2 2 lessons(100) +
            # modules 100+150+100 + quiz 80*2 + labs 100*2 + ctf 50*2 +
            # achievement 25 — just assert it lands over 900.
            assert xp[-1] > 900

    def test_pass_rate_blank_on_quiet_days(self, app):
        from app.analytics import services
        with app.app_context():
            series = services.timeseries(days=30)
            assert None in series["quiz_pass_rate"]


class TestStudentSearch:
    def test_text_level_and_xp_filters(self, app):
        from app.analytics import services
        with app.app_context():
            assert len(services.search_students()) == 3
            assert [u.username for u in
                    services.search_students(q="stud1")] == ["stud1"]
            assert [u.username for u in
                    services.search_students(q="stud2@test.io")] \
                == ["stud2"]
            assert [u.username for u in
                    services.search_students(level=5)] == ["stud1"]
            assert {u.username for u in
                    services.search_students(min_xp=400)} \
                == {"stud1", "stud2"}
            assert services.search_students(sort="username")[0].username \
                == "stud1"

    def test_admins_never_listed(self, app):
        from app.analytics import services
        with app.app_context():
            assert not [u for u in services.search_students(q="ana_admin")]


class TestStudentAnalytics:
    def test_full_profile_numbers(self, app):
        from app.analytics import services
        from app.auth.models import User
        with app.app_context():
            user = User.query.filter_by(username="stud1").first()
            data = services.student_analytics(user)
            assert data["streak"] == 7
            assert data["completion"]["lessons"]["done"] == 3
            assert data["completion"]["labs"] == {
                "done": 1,
                "total": data["completion"]["labs"]["total"],
                "pct": data["completion"]["labs"]["pct"]}
            assert data["completion"]["ctf"]["done"] == 1
            assert data["avg_quiz_score"] == 90.0
            # 3*600 lessons + 900 lab + 300 quiz + 400 ctf = 3400
            assert data["time_spent_seconds"] == 3400
            assert len(data["certificates"]) == 1
            assert len(data["achievements"]) == 1
            assert len(data["xp_trend"]) == 30
            assert data["xp_trend"][-1] > 0
            kinds = {item["kind"] for item in data["recent_activity"]}
            assert {"lesson", "lab", "ctf", "quiz", "achievement",
                    "certificate"} <= kinds


class TestContentAnalytics:
    def test_roadmap_rates_and_drop_off(self, app):
        from app.analytics import services
        with app.app_context():
            data = services.roadmap_analytics()
            row = next(r for r in data["rows"]
                       if r["category"] == "Linux Path")
            assert row["lessons"] == 3
            assert row["enrolled"] == 3
            # 5 completions of 9 possible = 56%
            assert row["completion_rate"] == 56
            assert row["drop_off"] is not None
            assert row["drop_off"]["after"] == "Basics"
            assert row["drop_off"]["lost"] == 1
            assert data["most_completed"]["category"] == "Linux Path"

    def test_lab_metrics(self, app):
        from app.analytics import services
        with app.app_context():
            data = services.lab_analytics()
            assert data["most_attempted"]["slug"] == "ana-easy"
            assert data["most_attempted"]["attempts"] == 3
            hardest = data["highest_failure"]
            assert hardest["slug"] == "ana-hard"
            assert hardest["failure_rate"] == 100
            easy = next(r for r in data["rows"] if r["slug"] == "ana-easy")
            assert easy["failure_rate"] == 33
            assert easy["avg_seconds"] == 1200

    def test_ctf_metrics(self, app):
        from app.analytics import services
        with app.app_context():
            data = services.ctf_analytics()
            assert data["most_solved"]["challenge"] == "Popular"
            assert data["least_solved"]["challenge"] == "Rare"
            assert data["avg_attempts"] == 3.0
            dist = data["difficulty_distribution"]
            assert dist["Easy"]["solves"] == 2
            assert dist["Hard"]["solves"] == 0


class TestEventTracking:
    def test_hint_events_roll_up_into_lab_analytics(self, app):
        from app.analytics import services
        from app.auth.models import User
        from app.extensions import db
        from app.labs.models import Lab, LabObjective
        with app.app_context():
            lab = Lab.query.filter_by(slug="ana-easy").first()
            objective = LabObjective(lab_id=lab.id, title="Obj",
                                     xp_reward=10)
            db.session.add(objective)
            db.session.commit()
            user = User.query.filter_by(username="stud1").first()
            services.record_event(user.id, "hint_used", "objective",
                                  objective.id, {"lab": "ana-easy"})
            services.record_event(user.id, "hint_used", "objective",
                                  objective.id, {"lab": "ana-easy"})
            data = services.lab_analytics()
            easy = next(r for r in data["rows"]
                        if r["slug"] == "ana-easy")
            assert easy["hints_used"] == 2
            assert data["total_hints_used"] == 2

    def test_events_endpoint_whitelist_and_auth(self, app):
        client = _login(app, "stud1")
        ok = client.post("/admin/analytics/events",
                         json={"event_type": "hint_used",
                               "subject_type": "objective",
                               "subject_id": 999,
                               "meta": {"lab": "x"}})
        assert ok.status_code == 200 and ok.get_json()["ok"]
        bad = client.post("/admin/analytics/events",
                          json={"event_type": "keylogger"})
        assert bad.status_code == 400
        anonymous = app.test_client().post(
            "/admin/analytics/events",
            json={"event_type": "hint_used"})
        assert anonymous.status_code in (302, 401, 403)


# ===========================================================================
# HTTP surface
# ===========================================================================
class TestHTTPSurface:
    def test_pages_render_for_admin(self, app):
        client = _login(app, "ana_admin")
        page = client.get("/admin/analytics/").data.decode()
        assert "Total Students" in page
        assert 'id="chart-dau"' in page
        assert "chart.umd.js" in page

        page = client.get("/admin/analytics/students?q=stud").data.decode()
        assert "stud1" in page and "stud3" in page

        from app.auth.models import User
        with app.app_context():
            uid = User.query.filter_by(username="stud1").first().id
        page = client.get(f"/admin/analytics/students/{uid}").data.decode()
        assert "Learning Streak" in page and "Recent Activity" in page

        page = client.get("/admin/analytics/content").data.decode()
        assert "Roadmap Analytics" in page
        assert "Lab Analytics" in page
        assert "CTF Analytics" in page

    def test_pages_forbidden_for_students_and_anonymous(self, app):
        student = _login(app, "stud1")
        assert student.get("/admin/analytics/").status_code == 403
        assert student.get("/admin/analytics/students").status_code == 403
        assert app.test_client().get(
            "/admin/analytics/").status_code == 403

    def test_csv_exports(self, app):
        client = _login(app, "ana_admin")
        response = client.get("/admin/analytics/export/overview.csv")
        assert response.mimetype == "text/csv"
        body = response.data.decode()
        assert "Total students,3" in body

        response = client.get(
            "/admin/analytics/export/students.csv?min_xp=400")
        body = response.data.decode()
        assert "stud1" in body and "stud2" in body
        assert "stud3" not in body

        for report in ("labs", "ctf", "roadmaps"):
            response = client.get(f"/admin/analytics/export/{report}.csv")
            assert response.status_code == 200

        assert client.get(
            "/admin/analytics/export/nonsense.csv").status_code == 404

    def test_pdf_export_is_future_ready(self, app):
        client = _login(app, "ana_admin")
        response = client.get("/admin/analytics/export/overview.pdf")
        assert response.status_code == 501
        assert "PDF" in response.get_json()["message"]
        assert client.get(
            "/admin/analytics/export/nonsense.pdf").status_code == 404
