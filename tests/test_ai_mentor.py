"""Tests for YC-032.1 — CyberMentor Core Platform."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0321ai-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_ai.db"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["AI_PROVIDER"] = "mock"
os.environ["AI_ENABLED"] = "true"

import pytest  # noqa: E402

from app.core.ai import (  # noqa: E402
    AIConfig,
    ChatResponse,
    MentorContext,
    Message,
    MockProvider,
    available_providers,
    health,
    models,
)
from app.core.ai import memory  # noqa: E402
from app.core.ai.context import context_from_dict  # noqa: E402
from app.core.ai.manager import AIManager, set_manager  # noqa: E402
from app.core.ai.mentor import ask_with_context  # noqa: E402
from app.core.ai.prompts import (  # noqa: E402
    SYSTEM_PROMPT,
    build_system_message,
)
from app.core.ai.providers import (  # noqa: E402
    PROVIDERS,
    BaseProvider,
    register_provider,
)


def _mock_manager() -> AIManager:
    cfg = AIConfig(provider="mock", enabled=True)
    mgr = AIManager(cfg)
    mgr.set_provider(MockProvider(cfg, "Test response from CyberMentor."))
    set_manager(mgr)
    return mgr


# ===========================================================================
# Types
# ===========================================================================
class TestTypes:
    def test_message(self):
        m = Message(role="user", content="Hello")
        assert m.to_dict() == {"role": "user", "content": "Hello"}

    def test_chat_response(self):
        r = ChatResponse(content="Hi", provider="mock", tokens_used=5)
        d = r.to_dict()
        assert d["content"] == "Hi"
        assert d["tokens_used"] == 5

    def test_ai_config_from_env(self):
        cfg = AIConfig.from_env()
        assert cfg.provider == "mock"  # set in os.environ above
        assert cfg.enabled is True

    def test_mentor_context_summary(self):
        ctx = MentorContext(username="Ayush", level=25, xp=5000,
                            completed_labs=["soc-fundamentals"],
                            current_lab="soc-capstone")
        s = ctx.summary()
        assert "Ayush" in s
        assert "Level 25" in s
        assert "soc-capstone" in s


# ===========================================================================
# Providers
# ===========================================================================
class TestProviders:
    def test_mock_provider(self):
        cfg = AIConfig(provider="mock")
        p = MockProvider(cfg, "Hello!")
        r = p.chat([Message(role="user", content="Hi")])
        assert r.content == "Hello!"
        assert p.call_count == 1

    def test_provider_registry(self):
        assert "openai" in PROVIDERS
        assert "anthropic" in PROVIDERS
        assert "mock" in PROVIDERS

    def test_register_custom_provider(self):
        class CustomProvider(BaseProvider):
            name = "custom"
            def chat(self, messages, **kw):
                return ChatResponse(content="custom!")
        register_provider("custom", CustomProvider)
        assert "custom" in PROVIDERS

    def test_health_check(self):
        cfg = AIConfig(provider="mock")
        p = MockProvider(cfg)
        h = p.health_check()
        assert h["status"] == "ok"

    def test_count_tokens(self):
        cfg = AIConfig(provider="mock")
        p = MockProvider(cfg)
        assert p.count_tokens("hello world") >= 1

    def test_list_models(self):
        cfg = AIConfig(provider="mock")
        p = MockProvider(cfg)
        assert len(p.list_models()) >= 1


# ===========================================================================
# Manager
# ===========================================================================
class TestManager:
    def test_chat_with_mock(self):
        mgr = _mock_manager()
        r = mgr.chat([Message(role="user", content="Hi")])
        assert "CyberMentor" in r.content

    def test_retry_on_failure(self):
        cfg = AIConfig(provider="mock", enabled=True)
        mgr = AIManager(cfg)
        # Use a provider that fails
        class FailProvider(BaseProvider):
            name = "fail"
            def chat(self, msgs, **kw):
                raise ConnectionError("down")
        mgr.set_provider(FailProvider(cfg))
        r = mgr.chat([Message(role="user", content="Hi")], retries=2)
        assert "unavailable" in r.content.lower() or "Error" in r.content

    def test_disabled_returns_message(self):
        cfg = AIConfig(provider="mock", enabled=False)
        mgr = AIManager(cfg)
        r = mgr.chat([Message(role="user", content="Hi")])
        assert "disabled" in r.content.lower()

    def test_usage_tracking(self):
        mgr = _mock_manager()
        mgr.chat([Message(role="user", content="X")])
        stats = mgr.usage()
        assert stats.total_requests >= 1


# ===========================================================================
# Context + Prompts
# ===========================================================================
class TestContext:
    def test_context_from_dict(self):
        ctx = context_from_dict({"username": "Test", "level": 10,
                                 "current_lab": "nmap-basics"})
        assert ctx.username == "Test"
        assert ctx.current_lab == "nmap-basics"

    def test_system_prompt_includes_context(self):
        ctx = MentorContext(username="Ayush", level=25)
        msg = build_system_message(ctx)
        assert "CyberMentor" in msg.content
        assert "Ayush" in msg.content
        assert msg.role == "system"

    def test_system_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT) > 100


# ===========================================================================
# Memory
# ===========================================================================
class TestMemory:
    def test_add_and_get(self):
        memory.clear(999)
        memory.add_message(999, Message(role="user", content="Hi"))
        memory.add_message(999, Message(role="assistant", content="Hey"))
        h = memory.get_history(999)
        assert len(h) == 2
        memory.clear(999)

    def test_max_history(self):
        memory.clear(998)
        for i in range(30):
            memory.add_message(998, Message(role="user",
                                            content=f"msg{i}"))
        h = memory.get_history(998)
        assert len(h) <= memory.MAX_HISTORY
        memory.clear(998)


# ===========================================================================
# Mentor (end-to-end with mock)
# ===========================================================================
class TestMentor:
    def test_ask_with_context(self):
        _mock_manager()
        ctx = MentorContext(username="Test", level=5)
        memory.clear(100)
        r = ask_with_context(ctx, 100, "What is SQL injection?")
        assert r.content != ""
        h = memory.get_history(100)
        assert len(h) == 2  # user + assistant
        memory.clear(100)


# ===========================================================================
# Services
# ===========================================================================
class TestServices:
    def test_available_providers(self):
        providers = available_providers()
        assert "mock" in providers
        assert "openai" in providers

    def test_health(self):
        _mock_manager()
        h = health()
        assert h["status"] == "ok"

    def test_models(self):
        _mock_manager()
        m = models()
        assert isinstance(m, list)


# ===========================================================================
# HTTP endpoints
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
        user = User(username="ai_tester", email="ai@t.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "ai_tester"


def _login(client, username):
    return client.post("/auth/login", data={
        "identifier": username, "password": "Str0ngPass!"},
        follow_redirects=True)


class TestHTTP:
    def test_health_endpoint(self, app):
        _mock_manager()
        with app.test_client() as client:
            r = client.get("/api/ai/health")
            assert r.status_code == 200
            assert r.get_json()["status"] == "ok"

    def test_models_endpoint(self, app):
        with app.test_client() as client:
            r = client.get("/api/ai/models")
            assert r.status_code == 200
            assert "models" in r.get_json()

    def test_chat_requires_login(self, app):
        with app.test_client() as client:
            r = client.post("/api/ai/chat",
                            json={"message": "Hi"})
            assert r.status_code in (401, 302)

    def test_chat_endpoint(self, app, student):
        _mock_manager()
        with app.test_client() as client:
            _login(client, student)
            r = client.post("/api/ai/chat",
                            json={"message": "What is XSS?"})
            assert r.status_code == 200
            body = r.get_json()
            assert body.get("content") != ""

    def test_chat_empty_message(self, app, student):
        with app.test_client() as client:
            _login(client, student)
            r = client.post("/api/ai/chat", json={"message": ""})
            assert r.status_code == 400
