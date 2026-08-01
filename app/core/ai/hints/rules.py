"""Hint rules — rate limiting, level gating, validation."""

from __future__ import annotations

import time

from app.core.ai.hints.models import HintConfig, MAX_STUDENT_LEVEL

# Track last hint request per user to enforce rate limit.
_last_request: dict[int, float] = {}


def check_rate_limit(user_id: int,
                     config: HintConfig) -> bool:
    """Return True if the request is rate-limited (should be blocked)."""
    now = time.time()
    last = _last_request.get(user_id, 0)
    if (now - last) < config.rate_limit_seconds:
        return True
    _last_request[user_id] = now
    return False


def reset_rate_limit(user_id: int) -> None:
    _last_request.pop(user_id, None)


def next_level(current_level: int,
               is_admin: bool = False,
               config: HintConfig | None = None) -> int:
    """Compute the next hint level."""
    config = config or HintConfig()
    max_level = 4 if (is_admin and config.allow_level_4) else MAX_STUDENT_LEVEL
    return min(current_level + 1, max_level)


def remaining_levels(current_level: int,
                     is_admin: bool = False) -> int:
    max_level = MAX_STUDENT_LEVEL
    if is_admin:
        max_level = 4
    return max(0, max_level - current_level)


def validate_request(objective_id: int, user_id: int) -> str | None:
    """Return an error string if invalid, or None if OK."""
    if objective_id <= 0:
        return "Invalid objective ID."
    if user_id <= 0:
        return "Invalid user."
    return None
