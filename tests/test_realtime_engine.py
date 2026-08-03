"""Tests for YC-033.2 — Real-Time Classroom Engine."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0332-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_rt.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.live.realtime.rooms import (  # noqa: E402
    join, leave, members, count, is_in_room, room_key,
)
from app.live.realtime.presence import (  # noqa: E402
    update as presence_update, get_status, all_presence, remove as presence_remove,
)
from app.live.realtime.chat import (  # noqa: E402
    send as chat_send, history as chat_history,
    delete_message, clear as chat_clear,
)
from app.live.realtime.polls import (  # noqa: E402
    create_poll, vote, results, close_poll, active_polls,
)
from app.live.realtime.announcements import (  # noqa: E402
    broadcast, pin, unpin, get_all, get_pinned,
)
from app.live.realtime.handraise import (  # noqa: E402
    raise_hand, lower_hand, clear_queue,
    call_on, is_raised, queue_count,
)
from app.live.realtime.heartbeat import (  # noqa: E402
    beat, is_alive, stale_users, clear as hb_clear,
)
from app.live.realtime.events import (  # noqa: E402
    emit, recent, clear as ev_clear,
)
from app.live.realtime.services import (  # noqa: E402
    join_classroom, leave_classroom, send_chat,
    chat_history as svc_chat_history,
    raise_hand as svc_raise, lower_hand as svc_lower,
    hand_queue as svc_hand_queue,
    create_poll as svc_create_poll, vote_poll,
    make_announcement, classroom_state, timeline,
)


SLUG = "test-class"


class TestRooms:
    def test_join_and_members(self):
        join(SLUG, 1, "Alice")
        join(SLUG, 2, "Bob")
        assert count(SLUG) == 2
        assert is_in_room(SLUG, 1)
        m = members(SLUG)
        assert len(m) == 2

    def test_leave(self):
        leave(SLUG, 2)
        assert count(SLUG) == 1
        assert not is_in_room(SLUG, 2)

    def test_room_key(self):
        assert room_key("abc") == "classroom:abc"


class TestPresence:
    def test_update_and_get(self):
        presence_update(SLUG, 1, "online")
        assert get_status(SLUG, 1) == "online"
        presence_update(SLUG, 1, "idle")
        assert get_status(SLUG, 1) == "idle"

    def test_all_presence(self):
        presence_update(SLUG, 1, "online")
        presence_update(SLUG, 3, "offline")
        result = all_presence(SLUG)
        assert len(result) >= 2

    def test_remove(self):
        presence_remove(SLUG, 3)
        assert get_status(SLUG, 3) == "offline"


class TestChat:
    def test_send_and_history(self):
        chat_clear(SLUG)
        chat_send(SLUG, 1, "Alice", "Hello world")
        chat_send(SLUG, 2, "Bob", "Hi Alice")
        h = chat_history(SLUG)
        assert len(h) == 2
        assert h[0]["text"] == "Hello world"

    def test_delete_own(self):
        chat_clear(SLUG)
        msg = chat_send(SLUG, 1, "Alice", "Delete me")
        assert delete_message(SLUG, msg["id"], user_id=1)
        assert len(chat_history(SLUG)) == 0

    def test_delete_as_instructor(self):
        chat_clear(SLUG)
        msg = chat_send(SLUG, 2, "Bob", "Bad message")
        assert delete_message(SLUG, msg["id"],
                              user_id=99, is_instructor=True)


class TestPolls:
    def test_create_and_vote(self):
        poll = create_poll(SLUG, "Favorite tool?",
                           ["Nmap", "Wireshark", "Burp"])
        assert poll["question"] == "Favorite tool?"
        assert vote(SLUG, poll["id"], 1, 0)   # Nmap = index 0
        assert vote(SLUG, poll["id"], 2, 1)   # Wireshark = index 1
        # Can't vote twice.
        assert not vote(SLUG, poll["id"], 1, 2)
        r = results(SLUG, poll["id"])
        assert r is not None
        assert r["totals"][0] == 1  # Nmap got 1 vote

    def test_close_poll(self):
        poll = create_poll(SLUG, "Close me?", ["Yes", "No"])
        assert close_poll(SLUG, poll["id"])
        assert len(active_polls(SLUG)) == 0 or \
            all(p["id"] != poll["id"] for p in active_polls(SLUG))


class TestAnnouncements:
    def test_broadcast_and_get(self):
        ann = broadcast(SLUG, "Welcome everyone!", "Instructor")
        assert ann["text"] == "Welcome everyone!"
        all_ann = get_all(SLUG)
        assert len(all_ann) >= 1

    def test_pin_unpin(self):
        ann = broadcast(SLUG, "Pinned msg", "Instructor")
        assert pin(SLUG, ann["id"])
        pinned = get_pinned(SLUG)
        assert len(pinned) >= 1
        assert unpin(SLUG, ann["id"])


class TestHandRaise:
    def test_raise_and_lower(self):
        clear_queue(SLUG)
        raise_hand(SLUG, 1, "Alice")
        raise_hand(SLUG, 2, "Bob")
        assert queue_count(SLUG) == 2
        assert is_raised(SLUG, 1)
        lower_hand(SLUG, 1)
        assert queue_count(SLUG) == 1
        assert not is_raised(SLUG, 1)

    def test_call_on(self):
        clear_queue(SLUG)
        raise_hand(SLUG, 3, "Charlie")
        result = call_on(SLUG, 3)
        assert result is not None
        assert queue_count(SLUG) == 0

    def test_clear_queue(self):
        raise_hand(SLUG, 1, "Alice")
        raise_hand(SLUG, 2, "Bob")
        cleared = clear_queue(SLUG)
        assert cleared >= 2


class TestHeartbeat:
    def test_beat_and_alive(self):
        hb_clear(SLUG)
        beat(SLUG, 1)
        assert is_alive(SLUG, 1)

    def test_stale_after_timeout(self):
        import time
        from app.live.realtime import heartbeat
        old_timeout = heartbeat.TIMEOUT
        heartbeat.TIMEOUT = 0  # instant timeout
        beat(SLUG, 99)
        time.sleep(0.01)
        stale = stale_users(SLUG)
        assert 99 in stale
        heartbeat.TIMEOUT = old_timeout


class TestEvents:
    def test_emit_and_recent(self):
        ev_clear(SLUG)
        emit(SLUG, "student_joined", 1, "Alice")
        emit(SLUG, "poll_opened", data={"poll_id": "p1"})
        evts = recent(SLUG, 5)
        assert len(evts) == 2
        assert evts[0]["type"] == "student_joined"


class TestServices:
    def test_join_and_leave(self):
        r = join_classroom("svc-test", 10, "Svc User")
        assert r["joined"] is True
        assert r["members"] == 1
        r2 = leave_classroom("svc-test", 10)
        assert r2["left"] is True
        assert r2["members"] == 0

    def test_chat(self):
        msg = send_chat("svc-test", 10, "User", "Hello")
        assert msg["message"] == "Hello"
        h = svc_chat_history("svc-test")
        assert len(h) >= 1

    def test_hand_raise(self):
        svc_raise("svc-test", 10, "User")
        q = svc_hand_queue("svc-test")
        assert len(q) >= 1
        svc_lower("svc-test", 10)

    def test_poll(self):
        p = svc_create_poll("svc-test", "Color?", ["Red", "Blue"])
        assert p["question"] == "Color?"
        assert vote_poll("svc-test", p["id"], 10, "Red")

    def test_announcement(self):
        ann = make_announcement("svc-test", "Hi all", "Teacher")
        assert ann["text"] == "Hi all"

    def test_classroom_state(self):
        state = classroom_state("svc-test")
        assert "members" in state
        assert "recent_chat" in state
        assert "active_polls" in state

    def test_timeline(self):
        tl = timeline("svc-test")
        assert isinstance(tl, list)


# ── HTTP API ──
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
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        u = User(username="rt_student", email="rt@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
    yield "rt_student"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestHTTPAPI:
    def test_join_api(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.post("/api/classroom/http-test/join")
            assert r.status_code == 200
            assert r.get_json()["joined"] is True

    def test_chat_api(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.post("/api/classroom/http-test/chat",
                            json={"message": "Hello API"})
            assert r.status_code == 200
            r2 = client.get("/api/classroom/http-test/chat")
            assert r2.status_code == 200

    def test_heartbeat_api(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.post("/api/classroom/http-test/heartbeat")
            assert r.status_code == 200

    def test_state_api(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.get("/api/classroom/http-test/state")
            assert r.status_code == 200
            assert "members" in r.get_json()

    def test_timeline_api(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.get("/api/classroom/http-test/timeline")
            assert r.status_code == 200
