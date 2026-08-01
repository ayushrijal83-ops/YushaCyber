# CyberMentor AI Framework

## Architecture

```
app/core/ai/
├── __init__.py      ← Public API exports
├── types.py         ← Message, ChatResponse, AIConfig, MentorContext, UsageStats
├── config.py        ← Environment-based config singleton
├── providers.py     ← BaseProvider (abstract), OpenAIProvider, AnthropicProvider,
│                       MockProvider, provider registry
├── manager.py       ← AIManager — retries, fallback, token accounting
├── context.py       ← build_context(user) — auto-collects from ORM
├── prompts.py       ← SYSTEM_PROMPT, build_system_message, prompt builders
├── memory.py        ← Per-session conversation history (in-memory)
├── mentor.py        ← ask(user, question) — the high-level API
├── models.py        ← Conversation dataclass
├── conversation.py  ← get/reset conversation
├── services.py      ← Public API: chat, health, models, usage
└── routes.py        ← Flask blueprint: POST /api/ai/chat,
                        GET /api/ai/health, GET /api/ai/models
```

## Provider System

Abstract `BaseProvider` with 5 methods: `chat()`, `stream_chat()`,
`health_check()`, `count_tokens()`, `list_models()`. Providers:

| Provider | Status | API |
|---|---|---|
| OpenAI | Implemented | `chat/completions` |
| Anthropic | Implemented | `/v1/messages` |
| Mock | Implemented | No API calls |
| Ollama | Interface ready | Register via `register_provider()` |
| Gemini | Interface ready | Register via `register_provider()` |

### Adding a provider

```python
from app.core.ai.providers import BaseProvider, register_provider

class OllamaProvider(BaseProvider):
    name = "ollama"
    def chat(self, messages, **kw):
        # Call Ollama API
        return ChatResponse(content="...", provider="ollama")

register_provider("ollama", OllamaProvider)
```

## Configuration

Environment variables:

```
AI_PROVIDER=openai       # openai | anthropic | mock | custom
AI_MODEL=gpt-4o-mini
AI_API_KEY=sk-...
AI_BASE_URL=             # optional, for Azure/OpenRouter
AI_TIMEOUT=30
AI_MAX_TOKENS=1024
AI_ENABLED=true
```

## Conversation Flow

1. Student sends message → `POST /api/ai/chat`
2. `build_context(user)` collects level, XP, labs, achievements
3. `build_system_message(context)` creates the system prompt
4. Memory appends conversation history
5. `AIManager.chat()` calls the provider with retries
6. Response saved to memory, returned to student

## Security

- Rate limiting via Flask production middleware
- Input validation (max 2000 chars)
- System prompt defines boundaries (no exploit code, ethical only)
- MockProvider for testing (no real API calls)
- API key stored in environment, never in code
