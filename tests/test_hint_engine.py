"""Tests for YC-032.3 — Smart Hint Engine."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0323-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_hints.db"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["AI_PROVIDER"] = "mock"

import pytest  # noqa: E402

from app.core.ai.hints import (  # noqa: E402
    HintConfig,
    HintResponse,
    get_hint,
    hint_summary,
    platform_stats,
)
from app.core.ai.hints.history import (  # noqa: E402
    clear as clear_history,
    clear_all as clear_all_history,
    current_level,
    hint_count,
    mark_solved,
    record,
    total_hints,
)
from app.core.ai.hints.rules import (  # noqa: E402
    check_rate_limit,
    next_level,
    remaining_levels,
    reset_rate_limit,
    validate_request,
)
from app.core.ai.hints.strategies import (  # noqa: E402
    build_hint_prompt,
    strategy_for_level,
)


# ===========================================================================
# Models
# ===========================================================================
class TestModels:
    def test_hint_config_penalty(self):
        cfg = HintConfig()
        assert cfg.penalty_for(1) == 0
        assert cfg.penalty_for(2) == 5
        assert cfg.penalty_for(3) == 10

    def test_hint_response_to_dict(self):
        r = HintResponse(level=2, hint="Check the logs.",
                         remaining_levels=1, xp_penalty=5)
        d = r.to_dict()
        assert d["level"] == 2
        assert d["xp_penalty"] == 5


# ===========================================================================
# Rules
# ===========================================================================
class TestRules:
    def test_next_level(self):
        assert next_level(0) == 1
        assert next_level(1) == 2
        assert next_level(2) == 3
        assert next_level(3) == 3  # capped for students

    def test_next_level_admin(self):
        cfg = HintConfig(allow_level_4=True)
        assert next_level(3, is_admin=True, config=cfg) == 4

    def test_remaining_levels(self):
        assert remaining_levels(1) == 2
        assert remaining_levels(3) == 0

    def test_validate_request(self):
        assert validate_request(0, 1) is not None
        assert validate_request(1, 0) is not None
        assert validate_request(1, 1) is None

    def test_rate_limit(self):
        cfg = HintConfig(rate_limit_seconds=1)
        reset_rate_limit(500)
        assert check_rate_limit(500, cfg) is False
        assert check_rate_limit(500, cfg) is True  # too soon
        reset_rate_limit(500)


# ===========================================================================
# Strategies
# ===========================================================================
class TestStrategies:
    def test_strategy_for_level(self):
        assert strategy_for_level(1) == "question"
        assert strategy_for_level(2) == "observation"
        assert strategy_for_level(3) == "concept"

    def test_build_hint_prompt(self):
        prompt = build_hint_prompt(
            2, "Identify the C2 domain",
            "SOC Hunt: DNS", "Expert",
            ["Check the DNS logs."], attempts=3)
        assert "Level 2" in prompt
        assert "C2 domain" in prompt
        assert "DNS" in prompt
        assert "NEVER reveal" in prompt


# ===========================================================================
# History
# ===========================================================================
class TestHistory:
    def test_record_and_query(self):
        clear_history(600)
        record(600, 10, "soc-lab", 1)
        record(600, 10, "soc-lab", 2)
        assert current_level(600, 10) == 2
        assert hint_count(600, 10) == 2
        assert total_hints(600) == 2
        clear_history(600)

    def test_mark_solved(self):
        clear_history(601)
        record(601, 20, "lab", 1)
        mark_solved(601, 20)
        from app.core.ai.hints.history import get_history
        recs = get_history(601, 20)
        assert recs[0].solved_after is True
        clear_history(601)


# ===========================================================================
# Analytics
# ===========================================================================
class TestAnalytics:
    def test_platform_stats(self):
        clear_all_history()
        record(1, 1, "lab-a", 1)
        record(1, 1, "lab-a", 2)
        record(2, 1, "lab-a", 1)
        stats = platform_stats()
        assert stats.total_requests == 3
        assert stats.avg_level >= 1.0
        assert len(stats.most_requested_objectives) >= 1
        clear_all_history()

    def test_empty_stats(self):
        clear_all_history()
        stats = platform_stats()
        assert stats.total_requests == 0


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
        user = User(username="hint_tester", email="hint@t.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "hint_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestIntegration:
    def test_get_hint_static(self, app, student):
        with app.app_context():
            from app.auth.models import User
            from app.labs.models import Lab
            u = User.query.filter_by(username="hint_tester").first()
            lab = Lab.query.filter_by(
                slug="forensics-fundamentals").first()
            obj = lab.objectives[0] if lab.objectives else None
            if obj and obj.hint1:
                clear_history(u.id)
                reset_rate_limit(u.id)
                resp = get_hint(u.id, obj.id)
                assert resp.level == 1
                assert resp.hint != ""
                assert resp.source == "static"
                clear_history(u.id)

    def test_get_hint_level_progression(self, app, student):
        with app.app_context():
            from app.auth.models import User
            from app.labs.models import Lab
            u = User.query.filter_by(username="hint_tester").first()
            lab = Lab.query.filter_by(
                slug="forensics-fundamentals").first()
            obj = lab.objectives[0]
            clear_history(u.id)
            reset_rate_limit(u.id)
            r1 = get_hint(u.id, obj.id)
            assert r1.level == 1
            reset_rate_limit(u.id)
            r2 = get_hint(u.id, obj.id)
            assert r2.level == 2
            reset_rate_limit(u.id)
            r3 = get_hint(u.id, obj.id)
            assert r3.level == 3
            clear_history(u.id)

    def test_hint_summary(self, app, student):
        with app.app_context():
            from app.auth.models import User
            from app.labs.models import Lab
            u = User.query.filter_by(username="hint_tester").first()
            lab = Lab.query.filter_by(
                slug="forensics-fundamentals").first()
            obj = lab.objectives[0]
            clear_history(u.id)
            reset_rate_limit(u.id)
            get_hint(u.id, obj.id)
            s = hint_summary(u.id, obj.id)
            assert s["current_level"] == 1
            assert s["hint_count"] == 1
            clear_history(u.id)

    def test_hint_api_endpoint(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            from app.labs.models import Lab
            with app.app_context():
                lab = Lab.query.filter_by(
                    slug="forensics-fundamentals").first()
                obj_id = lab.objectives[0].id
                from app.auth.models import User
                u = User.query.filter_by(
                    username="hint_tester").first()
                clear_history(u.id)
                reset_rate_limit(u.id)
            r = client.post("/api/ai/hint",
                            json={"objective_id": obj_id})
            assert r.status_code == 200
            body = r.get_json()
            assert body["level"] >= 1
            assert body["hint"] != ""

    def test_hint_api_missing_id(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.post("/api/ai/hint", json={})
            assert r.status_code == 400
