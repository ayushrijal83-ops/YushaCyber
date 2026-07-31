"""Tests for YC-031.6 — Universal Notification Framework."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0316-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_notif.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.core.notification import (  # noqa: E402
    NotificationData,
    NotificationType,
    Priority,
    UserPreferences,
)
from app.core.notification.templates import (  # noqa: E402
    achievement_unlocked,
    assessment_failed,
    assessment_passed,
    certificate_earned,
    lab_completed,
    level_up,
)
from app.core.notification.dispatcher import (  # noqa: E402
    InAppChannel,
    dispatch,
)


# ===========================================================================
# Types
# ===========================================================================
class TestTypes:
    def test_notification_type_enum(self):
        assert NotificationType.ACHIEVEMENT.value == "achievement"
        assert NotificationType.LEVEL_UP.value == "level_up"

    def test_priority_enum(self):
        assert Priority.CRITICAL.value == "critical"

    def test_notification_data_to_dict(self):
        n = NotificationData(user_id=1, title="Test",
                             message="Hello", type="system")
        d = n.to_dict()
        assert d["title"] == "Test"
        assert d["is_read"] is False

    def test_notification_is_read(self):
        n = NotificationData(read_at="2026-01-01")
        assert n.is_read is True
        n2 = NotificationData(read_at=None)
        assert n2.is_read is False

    def test_preferences_allows(self):
        p = UserPreferences(achievements=True, marketing=False)
        assert p.allows("achievements") is True
        assert p.allows("marketing") is False
        assert p.allows("unknown") is True  # defaults to True

    def test_preferences_to_dict(self):
        p = UserPreferences()
        d = p.to_dict()
        assert d["achievements"] is True
        assert d["marketing"] is False


# ===========================================================================
# Templates
# ===========================================================================
class TestTemplates:
    def test_achievement_unlocked(self):
        t, m, nt, lk = achievement_unlocked("SOC Master", 250)
        assert "SOC Master" in t
        assert "+250" in m
        assert nt == "achievement"

    def test_level_up(self):
        t, m, nt, lk = level_up(50)
        assert "50" in t
        assert nt == "level_up"

    def test_certificate_earned(self):
        t, m, nt, lk = certificate_earned("Blue Team Analyst")
        assert "Blue Team" in t
        assert nt == "certificate"

    def test_lab_completed(self):
        t, m, nt, lk = lab_completed("SOC Fundamentals", 150)
        assert "SOC Fundamentals" in t
        assert "+150" in m

    def test_assessment_passed(self):
        t, m, nt, lk = assessment_passed("Blue Team", "A")
        assert "Passed" in t
        assert "grade A" in m

    def test_assessment_failed(self):
        t, m, nt, lk = assessment_failed("Blue Team")
        assert nt == "assessment_failed"


# ===========================================================================
# Dispatcher
# ===========================================================================
class TestDispatcher:
    def test_in_app_channel(self):
        ch = InAppChannel()
        n = NotificationData(title="T")
        assert ch.deliver(n) is True

    def test_dispatch_returns_results(self):
        n = NotificationData(title="T")
        results = dispatch(n)
        assert "in_app" in results
        assert results["in_app"] is True


# ===========================================================================
# Integration — engine + services (needs app context)
# ===========================================================================
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
        from app.labs.forensics.seed import seed_forensics_labs
        seed_forensics_labs()
    yield application


@pytest.fixture(scope="module")
def user_id(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="notif_test", email="n@t.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
        return user.id


class TestEngine:
    def test_send_and_get(self, app, user_id):
        with app.app_context():
            from app.core.notification import send, get_unread
            from app.extensions import db
            n = send(user_id, "Test Notification", "Hello!",
                     ntype="system")
            db.session.commit()
            assert n.id is not None
            assert n.title == "Test Notification"
            unread = get_unread(user_id)
            assert any(u.id == n.id for u in unread)

    def test_mark_read(self, app, user_id):
        with app.app_context():
            from app.core.notification import (
                send, mark_read, get_unread)
            from app.extensions import db
            n = send(user_id, "Read Me")
            db.session.commit()
            assert mark_read(n.id) is True
            unread = get_unread(user_id)
            assert not any(u.id == n.id for u in unread)

    def test_mark_all_read(self, app, user_id):
        with app.app_context():
            from app.core.notification import (
                send, mark_all_read, get_unread)
            from app.extensions import db
            send(user_id, "Bulk 1")
            send(user_id, "Bulk 2")
            db.session.commit()
            count = mark_all_read(user_id)
            db.session.commit()
            assert count >= 2
            assert len(get_unread(user_id)) == 0

    def test_delete(self, app, user_id):
        with app.app_context():
            from app.core.notification import send, delete
            from app.extensions import db
            n = send(user_id, "Delete Me")
            db.session.commit()
            assert delete(n.id) is True
            assert delete(n.id) is False  # already gone

    def test_send_bulk(self, app, user_id):
        with app.app_context():
            from app.core.notification import send_bulk
            from app.extensions import db
            count = send_bulk([user_id], "Broadcast", "Hi all")
            db.session.commit()
            assert count == 1

    def test_notification_summary(self, app, user_id):
        with app.app_context():
            from app.core.notification import notification_summary
            s = notification_summary(user_id)
            assert "unread_count" in s
            assert "recent" in s

    def test_notify_achievement_helper(self, app, user_id):
        with app.app_context():
            from app.core.notification import notify_achievement
            from app.extensions import db
            n = notify_achievement(user_id, "SOC Rookie", 50)
            db.session.commit()
            assert "SOC Rookie" in n.title

    def test_notify_level_up_helper(self, app, user_id):
        with app.app_context():
            from app.core.notification import notify_level_up
            from app.extensions import db
            n = notify_level_up(user_id, 42)
            db.session.commit()
            assert "42" in n.title


class TestBackwardCompat:
    def test_existing_flash_still_works(self, app):
        """Flash messages are independent — not affected."""
        with app.test_request_context():
            from flask import flash, get_flashed_messages
            flash("Test flash", "success")
            msgs = get_flashed_messages()
            assert "Test flash" in msgs

    def test_existing_notification_model(self, app):
        with app.app_context():
            from app.community.models import Notification
            assert Notification.__tablename__ == "notifications"
