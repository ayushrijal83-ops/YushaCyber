"""Lab engine types — enums, dataclasses, workspace abstraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class LabType(str, Enum):
    LINUX = "linux"
    NETWORK = "network"
    WEB = "web"
    FORENSICS = "forensics"
    SOC = "soc"
    CRYPTO = "crypto"
    NMAP = "nmap"
    WIRESHARK = "wireshark"
    PYTHON = "python"
    WINDOWS = "windows"
    SQLI = "sqli"
    XSS = "xss"
    MALWARE = "malware"


class ObjectiveKind(str, Enum):
    RUN_COMMAND = "run_command"
    ANSWER_QUESTION = "answer_question"
    UPLOAD_FILE = "upload_file"
    CAPTURE_FLAG = "capture_flag"
    CLICK_TARGET = "click_target"
    VISIT_URL = "visit_url"
    READ_FILE = "read_file"
    MODIFY_FILE = "modify_file"
    COMPLETE_SCENARIO = "complete_scenario"


class EventKind(str, Enum):
    STUDENT_JOINED = "student_joined"
    OBJECTIVE_COMPLETED = "objective_completed"
    HINT_USED = "hint_used"
    XP_AWARDED = "xp_awarded"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    AI_MENTOR_ASKED = "ai_mentor_asked"
    LAB_COMPLETED = "lab_completed"
    LAB_RESET = "lab_reset"


@dataclass
class LabObjectiveDef:
    """One objective inside a lab."""
    id: str = ""
    title: str = ""
    description: str = ""
    kind: str = "run_command"
    expected: str = ""
    hint: str = ""
    xp: int = 50
    order: int = 0
    optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LabDef:
    """Complete lab definition — registered in the registry."""
    slug: str = ""
    title: str = ""
    description: str = ""
    lab_type: str = "linux"
    difficulty: str = "Easy"
    category: str = ""
    xp_total: int = 0
    estimated_minutes: int = 30
    objectives: list[LabObjectiveDef] = field(default_factory=list)
    workspace_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug, "title": self.title,
            "description": self.description,
            "lab_type": self.lab_type, "difficulty": self.difficulty,
            "category": self.category, "xp_total": self.xp_total,
            "estimated_minutes": self.estimated_minutes,
            "objectives": [o.to_dict() for o in self.objectives],
        }


@dataclass
class Workspace:
    """Abstract workspace — future implementations (terminal, browser,
    code editor, packet viewer) inherit from this."""
    workspace_type: str = "generic"
    config: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.workspace_type, "config": self.config,
                "state": self.state}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Workspace:
        return cls(workspace_type=data.get("type", "generic"),
                   config=data.get("config", {}),
                   state=data.get("state", {}))
