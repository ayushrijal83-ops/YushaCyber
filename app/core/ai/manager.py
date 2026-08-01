"""AI Manager — central orchestrator for AI requests.

Handles provider selection, retries, timeouts, fallback,
logging, and token accounting.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.ai.config import get_config
from app.core.ai.providers import BaseProvider, get_provider
from app.core.ai.types import AIConfig, ChatResponse, Message, UsageStats

logger = logging.getLogger(__name__)


class AIManager:
    """Central AI request orchestrator."""

    def __init__(self, config: AIConfig | None = None) -> None:
        self.config = config or get_config()
        self._provider: BaseProvider | None = None
        self._stats = UsageStats(provider=self.config.provider,
                                 model=self.config.model)

    @property
    def provider(self) -> BaseProvider:
        if self._provider is None:
            self._provider = get_provider(self.config)
        return self._provider

    def set_provider(self, provider: BaseProvider) -> None:
        """Override the provider (e.g. for testing)."""
        self._provider = provider

    def chat(self, messages: list[Message],
             retries: int = 2, **kwargs: Any) -> ChatResponse:
        """Send a chat request with retry logic."""
        if not self.config.enabled:
            return ChatResponse(
                content="AI is currently disabled.",
                provider="none", model="none")

        last_error = ""
        for attempt in range(max(1, retries)):
            try:
                response = self.provider.chat(messages, **kwargs)
                self._stats.total_requests += 1
                self._stats.total_tokens += response.tokens_used
                if "[AI Error]" not in response.content:
                    return response
                last_error = response.content
            except Exception as exc:
                last_error = str(exc)
                logger.warning("AI request failed (attempt %d): %s",
                               attempt + 1, exc)
                self._stats.failed_requests += 1

        self._stats.failed_requests += 1
        return ChatResponse(
            content=f"AI temporarily unavailable. {last_error}",
            provider=self.config.provider,
            model=self.config.model)

    def health(self) -> dict[str, Any]:
        """Check provider health."""
        try:
            return self.provider.health_check()
        except Exception as exc:
            return {"provider": self.config.provider,
                    "status": "error", "error": str(exc)}

    def models(self) -> list[str]:
        """List available models."""
        try:
            return self.provider.list_models()
        except Exception:
            return []

    def usage(self) -> UsageStats:
        """Return usage statistics."""
        return self._stats


# Module-level singleton.
_MANAGER: AIManager | None = None


def get_manager() -> AIManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = AIManager()
    return _MANAGER


def set_manager(manager: AIManager) -> None:
    global _MANAGER
    _MANAGER = manager
