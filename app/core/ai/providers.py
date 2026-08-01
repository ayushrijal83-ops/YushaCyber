"""AI providers — abstract interface + implementations.

Every provider implements the same 5 methods. No provider-specific
code exists outside this file. Adding a new provider = one class.
"""

from __future__ import annotations

import abc
from typing import Any, Iterator

from app.core.ai.types import AIConfig, ChatResponse, Message


class BaseProvider(abc.ABC):
    """Abstract AI provider interface."""

    name: str = "base"

    def __init__(self, config: AIConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def chat(self, messages: list[Message],
             **kwargs: Any) -> ChatResponse:
        """Synchronous chat completion."""

    def stream_chat(self, messages: list[Message],
                    **kwargs: Any) -> Iterator[str]:
        """Streaming chat (default: yield full response)."""
        response = self.chat(messages, **kwargs)
        yield response.content

    def health_check(self) -> dict[str, Any]:
        """Check provider health."""
        return {"provider": self.name, "status": "ok",
                "model": self.config.model}

    def count_tokens(self, text: str) -> int:
        """Estimate token count (rough: 4 chars ≈ 1 token)."""
        return max(1, len(text) // 4)

    def list_models(self) -> list[str]:
        """List available models."""
        return [self.config.model]


class OpenAIProvider(BaseProvider):
    """OpenAI-compatible provider (also works with Azure, OpenRouter)."""

    name = "openai"

    def chat(self, messages: list[Message],
             **kwargs: Any) -> ChatResponse:
        import json
        import urllib.request
        import urllib.error

        url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        body = json.dumps({
            "model": kwargs.get("model") or self.config.model,
            "messages": [m.to_dict() for m in messages],
            "max_tokens": kwargs.get("max_tokens") or self.config.max_tokens,
            "temperature": kwargs.get("temperature", self.config.temperature),
        }).encode()
        req = urllib.request.Request(url, data=body, headers=headers,
                                     method="POST")
        try:
            with urllib.request.urlopen(
                    req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read())
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            usage = data.get("usage", {})
            return ChatResponse(
                content=msg.get("content", ""),
                model=data.get("model", self.config.model),
                provider=self.name,
                tokens_used=usage.get("total_tokens", 0),
                finish_reason=choice.get("finish_reason", ""),
            )
        except (urllib.error.URLError, TimeoutError, Exception) as exc:
            return ChatResponse(
                content=f"[AI Error] {type(exc).__name__}: {exc}",
                provider=self.name, model=self.config.model)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider (interface-ready)."""

    name = "anthropic"

    def chat(self, messages: list[Message],
             **kwargs: Any) -> ChatResponse:
        import json
        import urllib.request

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }
        # Anthropic separates system from user messages.
        system = ""
        user_msgs = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                user_msgs.append({"role": m.role, "content": m.content})
        body = json.dumps({
            "model": kwargs.get("model") or self.config.model,
            "max_tokens": kwargs.get("max_tokens") or self.config.max_tokens,
            "system": system,
            "messages": user_msgs,
        }).encode()
        req = urllib.request.Request(url, data=body, headers=headers,
                                     method="POST")
        try:
            with urllib.request.urlopen(
                    req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read())
            content_blocks = data.get("content", [])
            text = "".join(b.get("text", "") for b in content_blocks
                          if b.get("type") == "text")
            usage = data.get("usage", {})
            return ChatResponse(
                content=text,
                model=data.get("model", self.config.model),
                provider=self.name,
                tokens_used=(usage.get("input_tokens", 0)
                             + usage.get("output_tokens", 0)),
            )
        except Exception as exc:
            return ChatResponse(
                content=f"[AI Error] {type(exc).__name__}: {exc}",
                provider=self.name, model=self.config.model)


class MockProvider(BaseProvider):
    """Mock provider for testing — no API calls."""

    name = "mock"

    def __init__(self, config: AIConfig,
                 response: str = "Mock AI response.") -> None:
        super().__init__(config)
        self._response = response
        self.call_count = 0
        self.last_messages: list[Message] = []

    def chat(self, messages: list[Message],
             **kwargs: Any) -> ChatResponse:
        self.call_count += 1
        self.last_messages = messages
        return ChatResponse(
            content=self._response,
            model=self.config.model,
            provider=self.name,
            tokens_used=len(self._response) // 4,
        )

    def health_check(self) -> dict[str, Any]:
        return {"provider": "mock", "status": "ok",
                "model": "mock-model"}


# Provider registry.
PROVIDERS: dict[str, type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "mock": MockProvider,
}


def get_provider(config: AIConfig) -> BaseProvider:
    """Instantiate the configured provider."""
    cls = PROVIDERS.get(config.provider, OpenAIProvider)
    return cls(config)


def register_provider(name: str, cls: type[BaseProvider]) -> None:
    """Register a custom provider (e.g. Ollama, Gemini)."""
    PROVIDERS[name] = cls
