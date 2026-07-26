"""Scenario registry — maps alert codes to IR decision configurations.

Each entry defines the correct and wrong actions per IR phase for a
specific alert. The SOC simulator's ``_take_action`` handler looks
up the active alert's scenario from this registry.

Adding a new scenario = adding one dict entry here. No code changes.
"""

from __future__ import annotations

from typing import Any

# Registry: alert_code → scenario dict
_SCENARIOS: dict[str, dict[str, Any]] = {}


def register(alert_code: str, scenario: dict[str, Any]) -> None:
    """Register a scenario config for an alert code."""
    _SCENARIOS[alert_code] = scenario


def get(alert_code: str) -> dict[str, Any]:
    """Retrieve the scenario for an alert, or empty dict."""
    return _SCENARIOS.get(alert_code, {})


def all_scenarios() -> dict[str, dict[str, Any]]:
    """All registered scenarios (for admin display)."""
    return dict(_SCENARIOS)
