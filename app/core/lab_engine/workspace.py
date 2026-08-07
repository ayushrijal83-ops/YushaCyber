"""Lab workspace — abstract workspace lifecycle.

Future implementations (terminal, browser, code editor) plug in
via the registry. The engine doesn't know about specifics.
"""

from __future__ import annotations

from typing import Any

from app.core.lab_engine.registry import create_workspace
from app.core.lab_engine.types import Workspace


def init_workspace(lab_type: str,
                   config: dict[str, Any] | None = None
                   ) -> Workspace:
    """Create a fresh workspace for a lab type."""
    return create_workspace(lab_type, config)


def restore_workspace(data: dict[str, Any]) -> Workspace:
    """Restore a workspace from saved state."""
    return Workspace.from_dict(data)
