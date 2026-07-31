"""Achievement rules — unlock condition evaluation.

Each rule is a pure function that checks whether a student's
progress meets a requirement. Rules are registered by name and
looked up at evaluation time.
"""

from __future__ import annotations

from typing import Any, Callable

# Rule registry: condition_type → checker function.
# Each checker receives (requirement_dict, metrics_dict) → bool.
_RULES: dict[str, Callable[[dict, dict], bool]] = {}


def register_rule(name: str) -> Callable:
    """Decorator to register a rule checker."""
    def wrapper(fn: Callable[[dict, dict], bool]) -> Callable:
        _RULES[name] = fn
        return fn
    return wrapper


def evaluate_rule(requirement: dict[str, Any],
                  metrics: dict[str, Any]) -> bool:
    """Evaluate one requirement against student metrics."""
    rule_type = requirement.get("type", "")
    checker = _RULES.get(rule_type)
    if checker is None:
        return False
    return checker(requirement, metrics)


def evaluate_all(requirements: list[dict[str, Any]],
                 metrics: dict[str, Any]) -> bool:
    """All requirements must pass (AND logic)."""
    if not requirements:
        return True
    return all(evaluate_rule(r, metrics) for r in requirements)


def available_rules() -> list[str]:
    """List registered rule names."""
    return sorted(_RULES.keys())


# ---------------------------------------------------------------------------
# Built-in rules (backward-compatible with existing condition_type values)
# ---------------------------------------------------------------------------

@register_rule("lab_completed")
def _lab_completed(req: dict, metrics: dict) -> bool:
    return metrics.get("lab_completed", 0) >= req.get("value", 1)


@register_rule("soc_lab_completed")
def _soc_lab_completed(req: dict, metrics: dict) -> bool:
    return metrics.get("soc_lab_completed", 0) >= req.get("value", 1)


@register_rule("complete_scenario")
def _complete_scenario(req: dict, metrics: dict) -> bool:
    slug = req.get("slug", "")
    return slug in metrics.get("completed_slugs", set())


@register_rule("complete_track")
def _complete_track(req: dict, metrics: dict) -> bool:
    track = req.get("track", "")
    return track in metrics.get("completed_tracks", set())


@register_rule("perfect_score")
def _perfect_score(req: dict, metrics: dict) -> bool:
    return metrics.get("perfect_scores", 0) >= req.get("value", 1)


@register_rule("speed_run")
def _speed_run(req: dict, metrics: dict) -> bool:
    threshold = req.get("value", 0)
    best_time = metrics.get("best_time_seconds", float("inf"))
    return 0 < best_time <= threshold


@register_rule("xp_milestone")
def _xp_milestone(req: dict, metrics: dict) -> bool:
    return metrics.get("total_xp", 0) >= req.get("value", 0)


@register_rule("level_milestone")
def _level_milestone(req: dict, metrics: dict) -> bool:
    return metrics.get("level", 0) >= req.get("value", 0)


@register_rule("certificate_earned")
def _certificate_earned(req: dict, metrics: dict) -> bool:
    slug = req.get("slug", "")
    return slug in metrics.get("certificates", set())


@register_rule("custom")
def _custom(req: dict, metrics: dict) -> bool:
    func_path = req.get("function", "")
    if not func_path:
        return False
    try:
        module_path, func_name = func_path.rsplit(".", 1)
        import importlib
        mod = importlib.import_module(module_path)
        func = getattr(mod, func_name)
        return bool(func(req, metrics))
    except (ImportError, AttributeError, TypeError, ValueError):
        return False
