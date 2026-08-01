"""Tests for YC-032.2 — Intelligent Context Engine."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0322-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_ctx.db"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["AI_PROVIDER"] = "mock"

import pytest  # noqa: E402

from app.core.ai.context_engine import (  # noqa: E402
    filter_for_ai,
    get_context,
    get_context_dict,
    get_context_summary,
    get_learning_profile,
    on_answer_submitted,
    on_hint_used,
    on_lab_start,
    on_page_visit,
)
from app.core.ai.context_engine.activity import (  # noqa: E402
    clear as clear_activity,
    get_activity,
    track,
)
from app.core.ai.context_engine.builder import invalidate_all  # noqa: E402
from app.core.ai.context_engine.models import FullContext  # noqa: E402
from app.core.ai.context_engine.tracker import (  # noqa: E402
    get_session,
    visit_page,
)


# ===========================================================================
# Models (pure unit tests)
# ===========================================================================
class TestModels:
    def test_full_context_to_dict(self):
        ctx = FullContext()
        d = ctx.to_dict()
        assert "user" in d
        assert "learning" in d
        assert "progress" in d
        assert "activity" in d
        assert "assessment" in d
        assert "achievements" in d
        assert "roadmap" in d

    def test_summary_text(self):
        ctx = FullContext()
        ctx.user.username = "Ayush"
        ctx.progress.level = 25
        ctx.progress.xp = 5000
        ctx.learning.current_lab = "soc-hunt-dns"
        ctx.learning.current_lab_title = "Hunt: DNS"
        s = ctx.summary_text()
        assert "Ayush" in s
        assert "Level 25" in s
        assert "Hunt: DNS" in s


# ===========================================================================
# Activity tracker
# ===========================================================================
class TestActivity:
    def test_track_and_get(self):
        clear_activity(900)
        track(900, "page_visit", page="/labs/", lab="nmap-basics")
        a = get_activity(900)
        assert a.current_page == "/labs/"
        assert "nmap-basics" in a.recent_labs
        assert a.last_action == "page_visit"
        clear_activity(900)

    def test_dedup_recent(self):
        clear_activity(901)
        track(901, "visit", lab="a")
        track(901, "visit", lab="a")
        a = get_activity(901)
        assert a.recent_labs.count("a") == 1
        clear_activity(901)


# ===========================================================================
# Session tracker
# ===========================================================================
class TestTracker:
    def test_visit_and_get(self):
        visit_page(800, "/dashboard/")
        visit_page(800, "/labs/")
        s = get_session(800)
        assert len(s["pages"]) == 2
        assert s["duration"] >= 0


# ===========================================================================
# Security filter
# ===========================================================================
class TestSecurity:
    def test_filter_removes_secrets(self):
        data = {
            "user": {"username": "Ayush"},
            "api_key": "sk-secret",
            "password": "hidden",
            "correct_answer": "42",
            "learning": {"current_lab": "soc"},
        }
        safe = filter_for_ai(data)
        assert "api_key" not in safe
        assert "password" not in safe
        assert "correct_answer" not in safe
        assert safe["user"]["username"] == "Ayush"
        assert safe["learning"]["current_lab"] == "soc"


# ===========================================================================
# Session event helpers
# ===========================================================================
class TestSessionEvents:
    def test_on_page_visit(self):
        clear_activity(700)
        on_page_visit(700, "/labs/soc", lab="soc-basics")
        a = get_activity(700)
        assert a.current_page == "/labs/soc"
        clear_activity(700)

    def test_on_lab_start(self):
        clear_activity(701)
        on_lab_start(701, "nmap-basics")
        a = get_activity(701)
        assert a.last_action == "lab_start"
        clear_activity(701)

    def test_on_hint_used(self):
        clear_activity(702)
        on_hint_used(702)
        a = get_activity(702)
        assert a.last_action == "hint_used"
        clear_activity(702)

    def test_on_answer_submitted(self):
        clear_activity(703)
        on_answer_submitted(703, True)
        a = get_activity(703)
        assert a.last_action == "answer_passed"
        clear_activity(703)


# ===========================================================================
# Integration (needs app context)
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
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="ctx_tester", email="ctx@t.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "ctx_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestIntegration:
    def test_get_context(self, app, student):
        with app.app_context():
            from app.auth.models import User
            invalidate_all()
            u = User.query.filter_by(username="ctx_tester").first()
            ctx = get_context(u, current_lab="soc-hunt-dns")
            assert isinstance(ctx, FullContext)
            assert ctx.user.username == "ctx_tester"
            assert ctx.learning.current_lab == "soc-hunt-dns"
            assert ctx.progress.total_labs > 0

    def test_get_context_dict(self, app, student):
        with app.app_context():
            from app.auth.models import User
            u = User.query.filter_by(username="ctx_tester").first()
            d = get_context_dict(u)
            assert d["user"]["username"] == "ctx_tester"

    def test_get_context_summary(self, app, student):
        with app.app_context():
            from app.auth.models import User
            u = User.query.filter_by(username="ctx_tester").first()
            s = get_context_summary(u)
            assert "ctx_tester" in s

    def test_learning_profile(self, app, student):
        with app.app_context():
            from app.auth.models import User
            u = User.query.filter_by(username="ctx_tester").first()
            profile = get_learning_profile(u)
            assert profile.hint_dependency in ("low", "moderate", "high")

    def test_context_endpoint_admin_only(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.get("/api/ai/context")
            assert r.status_code == 403

    def test_caching(self, app, student):
        with app.app_context():
            from app.auth.models import User
            invalidate_all()
            u = User.query.filter_by(username="ctx_tester").first()
            ctx1 = get_context(u)
            ctx2 = get_context(u)
            # Same cached object.
            assert ctx1.user.user_id == ctx2.user.user_id
