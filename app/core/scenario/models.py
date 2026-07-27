"""Scenario and Objective dataclasses.

These are in-memory representations — NOT ORM models. They bridge
the existing ``Lab`` / ``LabObjective`` ORM rows and the new
service layer. A Scenario can be built from an ORM Lab, from a
plain dict, or programmatically.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.scenario.types import (
    Difficulty,
    ObjectiveType,
    ReportType,
    ValidationRule,
)


@dataclass
class Objective:
    """One task the student must complete."""

    id: int | None = None
    title: str = ""
    description: str = ""
    instruction: str = ""
    objective_type: str = ObjectiveType.CUSTOM.value
    validation: ValidationRule | None = None
    xp_reward: int = 0
    display_order: int = 0
    is_optional: bool = False
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.validation:
            d["validation"] = self.validation.to_dict()
        return d


@dataclass
class Scenario:
    """A complete interactive learning scenario."""

    id: int | None = None
    slug: str = ""
    title: str = ""
    description: str = ""
    category: str = ""
    difficulty: str = Difficulty.EASY.value
    estimated_minutes: int | None = None
    xp_reward: int = 0
    objectives: list[Objective] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    validation_rules: list[ValidationRule] = field(default_factory=list)
    completion_rules: dict[str, Any] = field(default_factory=dict)
    report_type: str = ReportType.CUSTOM.value
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["objectives"] = [o.to_dict() for o in self.objectives]
        d["validation_rules"] = [v.to_dict()
                                 for v in self.validation_rules]
        return d

    @property
    def required_objectives(self) -> list[Objective]:
        return [o for o in self.objectives if not o.is_optional]

    @property
    def total_xp(self) -> int:
        return self.xp_reward + sum(o.xp_reward
                                    for o in self.objectives)


def scenario_from_lab(lab) -> Scenario:
    """Build a Scenario from an ORM ``Lab`` row. Backward-compatible
    bridge — every existing lab works through this function."""
    objectives = []
    for obj in getattr(lab, "objectives", []) or []:
        validator_data = obj.get_validator_data()
        hints = [h for h in (getattr(obj, "hint1", None),
                              getattr(obj, "hint2", None),
                              getattr(obj, "hint3", None)) if h]
        objectives.append(Objective(
            id=obj.id,
            title=obj.title,
            description=getattr(obj, "description", "") or "",
            instruction=getattr(obj, "instruction", "") or "",
            objective_type=_infer_objective_type(obj.validator_type),
            validation=ValidationRule(obj.validator_type, validator_data),
            xp_reward=obj.xp_reward,
            display_order=getattr(obj, "display_order", 0),
            is_optional=getattr(obj, "is_optional", False),
            hints=hints,
        ))
    objectives.sort(key=lambda o: o.display_order)

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
        report_type=_infer_report_type(lab.slug),
    )


def scenario_from_dict(data: dict[str, Any]) -> Scenario:
    """Build a Scenario from a plain dict."""
    objectives = []
    for obj_data in data.get("objectives") or []:
        validation = None
        if obj_data.get("validation"):
            validation = ValidationRule.from_dict(obj_data["validation"])
        elif obj_data.get("validator_type"):
            validation = ValidationRule(
                obj_data["validator_type"],
                obj_data.get("validator_data") or {})
        objectives.append(Objective(
            id=obj_data.get("id"),
            title=obj_data.get("title", ""),
            description=obj_data.get("description", ""),
            instruction=obj_data.get("instruction", ""),
            objective_type=obj_data.get("objective_type",
                                        ObjectiveType.CUSTOM.value),
            validation=validation,
            xp_reward=obj_data.get("xp_reward", 0),
            display_order=obj_data.get("display_order", 0),
            is_optional=obj_data.get("is_optional", False),
            hints=obj_data.get("hints") or [],
        ))
    return Scenario(
        id=data.get("id"),
        slug=data.get("slug", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        category=data.get("category", ""),
        difficulty=data.get("difficulty", Difficulty.EASY.value),
        estimated_minutes=data.get("estimated_minutes"),
        xp_reward=data.get("xp_reward", 0),
        objectives=objectives,
        hints=data.get("hints") or [],
        report_type=data.get("report_type", ReportType.CUSTOM.value),
        metadata=data.get("metadata") or {},
    )


def _infer_objective_type(validator_type: str) -> str:
    """Map a validator type to a semantic objective type."""
    mapping = {
        "event_emitted": ObjectiveType.CUSTOM.value,
        "state_flag": ObjectiveType.ANSWER_QUESTION.value,
        "exact_command": ObjectiveType.EXECUTE_COMMAND.value,
        "exact_match": ObjectiveType.ANSWER_QUESTION.value,
        "multi_step": ObjectiveType.CUSTOM.value,
        "ordered_tasks": ObjectiveType.CUSTOM.value,
        "score_threshold": ObjectiveType.CUSTOM.value,
    }
    return mapping.get(validator_type, ObjectiveType.CUSTOM.value)


def _infer_report_type(slug: str) -> str:
    """Infer the report type from the lab slug."""
    if "forensics" in slug:
        return ReportType.FORENSICS.value
    if "hunt" in slug:
        return ReportType.HUNT.value
    if "assessment" in slug:
        return ReportType.ASSESSMENT.value
    if "soc" in slug:
        return ReportType.INCIDENT.value
    return ReportType.CUSTOM.value
