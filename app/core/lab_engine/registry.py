"""Lab registry — register lab types and definitions.

Lab implementations register themselves here. The engine
looks up lab definitions by slug or type without knowing
the implementation details.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.lab_engine.types import LabDef, Workspace

# {lab_type: factory_fn} — creates a Workspace for that type.
_workspace_factories: dict[str, Callable[..., Workspace]] = {}

# {slug: LabDef} — all registered lab definitions.
_lab_defs: dict[str, LabDef] = {}


def register_workspace(lab_type: str,
                       factory: Callable[..., Workspace]) -> None:
    """Register a workspace factory for a lab type."""
    _workspace_factories[lab_type] = factory


def create_workspace(lab_type: str,
                     config: dict[str, Any] | None = None
                     ) -> Workspace:
    """Create a workspace for the given lab type."""
    factory = _workspace_factories.get(lab_type)
    if factory:
        return factory(config or {})
    return Workspace(workspace_type=lab_type, config=config or {})


def register_lab(lab_def: LabDef) -> None:
    """Register a lab definition."""
    _lab_defs[lab_def.slug] = lab_def


def get_lab(slug: str) -> LabDef | None:
    return _lab_defs.get(slug)


def list_labs(lab_type: str | None = None) -> list[LabDef]:
    labs = list(_lab_defs.values())
    if lab_type:
        labs = [l for l in labs if l.lab_type == lab_type]
    return sorted(labs, key=lambda l: l.slug)


def registered_types() -> list[str]:
    return sorted(_workspace_factories.keys())


def clear() -> None:
    _workspace_factories.clear()
    _lab_defs.clear()
