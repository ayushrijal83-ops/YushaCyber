"""Scenario engine — unified scenario definition and lifecycle.

Wraps the existing ``Lab`` + ``LabObjective`` ORM models so every
interactive module (Digital Forensics, SOC, Networking, Nmap,
Wireshark, future AD/Cloud/API) shares the same scenario contract.

A **Scenario** is a plain dict built from any Lab row. New modules
can create scenarios programmatically without touching the ORM by
calling ``scenario_from_dict()``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Scenario:
    """In-memory representation of an interactive learning scenario."""

    id: int | None = None
    slug: str = ""
    title: str = ""
    description: str = ""
    category: str = ""
    difficulty: str = "Easy"
    estimated_minutes: int | None = None
    xp_reward: int = 0
    objectives: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    validation_rules: list[dict[str, Any]] = field(default_factory=list)
    completion_status: str = "not_started"   # not_started | in_progress | completed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scenario_from_lab(lab) -> Scenario:
    """Build a Scenario from an ORM ``Lab`` row (backward-compatible).

    Every existing lab works through this function without any model
    changes — we read the Lab's relationships at runtime.
    """
    objectives = []
    for obj in getattr(lab, "objectives", []) or []:
        objectives.append({
            "id": obj.id,
            "title": obj.title,
            "description": getattr(obj, "description", "") or "",
            "instruction": getattr(obj, "instruction", "") or "",
            "validator_type": obj.validator_type,
            "validator_data": obj.get_validator_data(),
            "xp_reward": obj.xp_reward,
            "display_order": getattr(obj, "display_order", 0),
            "is_optional": getattr(obj, "is_optional", False),
            "hints": [
                getattr(obj, "hint1", None),
                getattr(obj, "hint2", None),
                getattr(obj, "hint3", None),
            ],
        })
    objectives.sort(key=lambda o: o.get("display_order", 0))
    category_name = ""
    if hasattr(lab, "category") and lab.category:
        category_name = getattr(lab.category, "name", "") or ""

    return Scenario(
        id=lab.id,
        slug=lab.slug,
        title=lab.title,
        description=getattr(lab, "description", "") or "",
        category=category_name,
        difficulty=lab.difficulty,
        estimated_minutes=getattr(lab, "estimated_minutes", None),
        xp_reward=lab.xp_reward,
        objectives=objectives,
    )


def scenario_from_dict(data: dict[str, Any]) -> Scenario:
    """Build a Scenario from a plain dict (for programmatic use)."""
    return Scenario(
        id=data.get("id"),
        slug=data.get("slug", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        category=data.get("category", ""),
        difficulty=data.get("difficulty", "Easy"),
        estimated_minutes=data.get("estimated_minutes"),
        xp_reward=data.get("xp_reward", 0),
        objectives=data.get("objectives", []),
        evidence=data.get("evidence", []),
        tasks=data.get("tasks", []),
        validation_rules=data.get("validation_rules", []),
        completion_status=data.get("completion_status", "not_started"),
    )


def is_complete(scenario: Scenario,
                completed_objective_ids: set[int]) -> bool:
    """True when every required objective in the scenario is done."""
    for obj in scenario.objectives:
        if obj.get("is_optional"):
            continue
        if obj.get("id") not in completed_objective_ids:
            return False
    return True


def completion_ratio(scenario: Scenario,
                     completed_objective_ids: set[int]) -> float:
    """0.0 – 1.0 progress ratio (required objectives only)."""
    required = [o for o in scenario.objectives
                if not o.get("is_optional")]
    if not required:
        return 1.0
    done = sum(1 for o in required
               if o.get("id") in completed_objective_ids)
    return done / len(required)
