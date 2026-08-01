"""AI configuration — loads from environment variables."""

from __future__ import annotations

from app.core.ai.types import AIConfig

_CONFIG: AIConfig | None = None


def get_config() -> AIConfig:
    """Get or create the singleton config."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = AIConfig.from_env()
    return _CONFIG


def set_config(config: AIConfig) -> None:
    """Override config (for testing or admin changes)."""
    global _CONFIG
    _CONFIG = config


def is_enabled() -> bool:
    return get_config().enabled
