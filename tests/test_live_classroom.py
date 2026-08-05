"""Tests for YC-033.0 — Live Classroom Foundation."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

_TMPDIR = tempfile.mkdtemp(prefix="yc0330-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_live.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
    yield application


@pytest.fixture(scope="module")
def instructor(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="instructor1", email="ins@t.io",
                     is_admin=True)
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture(scope="module")
def student_id(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="student_live", email="sl@t.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestModels:
    def test_create_class(self, app, instructor):
        with app.app_context():
            from app.live import services
            from app.extensions import db
            lc = services.create_class(
                instructor, "Intro to SOC",
                "intro-to-soc",
                description="Learn SOC basics.",
                capacity=20, status="scheduled",
                start_time=datetime.now(timezone.utc) + timedelta(hours=1))
            db.session.commit()
            assert lc.id is not None
            assert lc.slug == "intro-to-soc"
            assert lc.enrolled_count == 0
            assert not lc.is_full

    def test_get_by_slug(self, app):
        with app.app_context():
            from app.live.services import get_by_slug
            lc = get_by_slug("intro-to-soc")
            assert lc is not None
            assert lc.title == "Intro to SOC"


class TestEnrollment:
    def test_enroll(self, app, student_id):
        with app.app_context():
            from app.live import services
            from app.extensions import db
            lc = services.get_by_slug("intro-to-soc")
            e = services.enroll(student_id, lc.id)
            db.session.commit()
            assert e is not None
            assert e.attendance_status == "registered"
            assert lc.enrolled_count == 1

    def test_enroll_idempotent(self, app, student_id):
        with app.app_context():
            from app.live import services
            lc = services.get_by_slug("intro-to-soc")
            e = services.enroll(student_id, lc.id)
            assert e is not None

    def test_is_enrolled(self, app, student_id):
        with app.app_context():
            from app.live import services
            lc = services.get_by_slug("intro-to-soc")
            assert services.is_enrolled(student_id, lc.id)

    def test_capacity_limit(self, app, instructor):
        with app.app_context():
            from app.live import services
            from app.extensions import db
            lc = services.create_class(
                instructor, "Full Class", "full-class",
                capacity=1, status="scheduled")
            db.session.commit()
            from app.auth.models import User
            u1 = User(username="cap1", email="c1@t.io")
            u1.set_password("Str0ngPass!")
            u2 = User(username="cap2", email="c2@t.io")
            u2.set_password("Str0ngPass!")
            db.session.add_all([u1, u2])
            db.session.commit()
            services.enroll(u1.id, lc.id)
            db.session.commit()
            result = services.enroll(u2.id, lc.id)
            assert result is None  # full

    def test_unenroll(self, app, student_id):
        with app.app_context():
            from app.live import services
            from app.extensions import db
            lc = services.get_by_slug("intro-to-soc")
            services.unenroll(student_id, lc.id)
            db.session.commit()
            assert not services.is_enrolled(student_id, lc.id)
            # Re-enroll for later tests.
            services.enroll(student_id, lc.id)
            db.session.commit()


class TestAttendance:
    def test_mark_joined(self, app, student_id, instructor):
        with app.app_context():
            from app.live import services
            from app.extensions import db
            # Create a fresh class for attendance tests.
            lc = services.create_class(
                instructor, "Attendance Test", "att-test",
                capacity=20, status="scheduled",
                start_time=datetime.now(timezone.utc))
            db.session.commit()
            services.enroll(student_id, lc.id)
            services.start_class(lc)
            db.session.commit()
            e = services.mark_joined(student_id, lc.id)
            db.session.commit()
            assert e is not None
            assert e.attendance_status in ("present", "late")

    def test_mark_left(self, app, student_id, instructor):
        with app.app_context():
            from app.live import services
            from app.live.models import LiveClass
            from app.extensions import db
            lc = LiveClass.query.filter_by(slug="att-test").first()
            if lc is None:
                lc = services.create_class(
                    instructor, "Attendance Test", "att-test",
                    capacity=20, status="live",
                    start_time=datetime.now(timezone.utc))
                db.session.commit()
                services.enroll(student_id, lc.id)
                services.mark_joined(student_id, lc.id)
                db.session.commit()
            e = services.mark_left(student_id, lc.id)
            db.session.commit()
            assert e is not None
            assert e.left_at is not None

    def test_attendance_report(self, app):
        with app.app_context():
            from app.live import services
            from app.live.models import LiveClass
            lc = LiveClass.query.filter_by(slug="att-test").first()
            if lc is None:
                pytest.skip("att-test not found")
            report = services.attendance_report(lc.id)
            assert len(report) >= 1


class TestProviders:
    def test_jitsi_url(self):
        from app.live.providers import JitsiProvider
        p = JitsiProvider()
        url = p.generate_url("test-room")
        assert "meet.jit.si" in url
        assert "yushacyber" in url

    def test_provider_registry(self):
        from app.live.providers import PROVIDERS, get_provider
        assert "jitsi" in PROVIDERS
        assert "zoom" in PROVIDERS
        p = get_provider("jitsi")
        assert p.name == "jitsi"


class TestCalendar:
    def test_calendar_events(self, app):
        with app.app_context():
            from app.live.services import calendar_events
            events = calendar_events()
            assert isinstance(events, list)

    def test_class_to_dict(self, app, instructor):
        with app.app_context():
            from app.live import services
            from app.extensions import db
            lc = services.create_class(
                instructor, "Dict Test", "dict-test",
                capacity=10, status="live")
            lc.meeting_url = "https://meet.jit.si/test"
            db.session.commit()
            d = services.class_to_dict(lc, show_url=True)
            assert d["title"] == "Dict Test"
            assert d["status"] == "live"
            assert d["meeting_url"] == "https://meet.jit.si/test"


class TestPermissions:
    def test_is_instructor(self, app, instructor):
        with app.app_context():
            from app.live.services import get_by_slug
            lc = get_by_slug("intro-to-soc")
            from app.auth.models import User
            user = User.query.get(instructor)
            assert lc.is_instructor(user)


class TestHTTP:
    def test_class_list(self, app):
        with app.test_client() as client:
            r = client.get("/classes")
            assert r.status_code == 200

    def test_api_classes(self, app):
        with app.test_client() as client:
            r = client.get("/api/classes")
            assert r.status_code == 200
            assert isinstance(r.get_json(), list)

    def test_register_requires_login(self, app):
        with app.test_client() as client:
            r = client.post("/classes/intro-to-soc/register")
            assert r.status_code in (302, 401)

    def test_api_register(self, app):
        with app.test_client() as client:
            _login(client, "student_live")
            # Get class ID in the same app context.
            from app.live.models import LiveClass
            with app.app_context():
                lc = LiveClass.query.filter_by(slug="intro-to-soc").first()
                if lc is None:
                    pytest.skip("No class")
                cid = lc.id
            r = client.post("/api/classes/register",
                            json={"class_id": cid})
            assert r.status_code == 200

    def test_api_attendance(self, app):
        with app.test_client() as client:
            _login(client, "student_live")
            from app.live.models import LiveClass
            with app.app_context():
                lc = LiveClass.query.filter_by(slug="intro-to-soc").first()
                if lc is None:
                    pytest.skip("No class")
                cid = lc.id
            r = client.post("/api/classes/attendance",
                            json={"class_id": cid, "action": "join"})
            assert r.status_code == 200
