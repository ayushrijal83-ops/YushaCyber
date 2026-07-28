"""Report types — enums, section definitions, and dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ReportKind(str, Enum):
    """Every report type in YushaCyber."""
    LAB = "lab"
    INVESTIGATION = "investigation"
    THREAT_HUNT = "threat_hunt"
    INCIDENT = "incident"
    BLUE_TEAM = "blue_team"
    ASSESSMENT = "assessment"
    COMPLETION = "completion"
    CERTIFICATE_SUMMARY = "certificate_summary"


class OutputFormat(str, Enum):
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


class SectionKind(str, Enum):
    """Built-in section types the builder recognises."""
    EXECUTIVE_SUMMARY = "executive_summary"
    OBJECTIVES = "objectives"
    TIMELINE = "timeline"
    EVIDENCE = "evidence"
    FINDINGS = "findings"
    ROOT_CAUSE = "root_cause"
    MITRE = "mitre"
    CONTAINMENT = "containment"
    RECOVERY = "recovery"
    RECOMMENDATIONS = "recommendations"
    APPENDIX = "appendix"


SECTION_LABELS: dict[str, str] = {
    "executive_summary": "Executive Summary",
    "objectives": "Objectives",
    "timeline": "Timeline",
    "evidence": "Evidence",
    "findings": "Findings",
    "root_cause": "Root Cause",
    "mitre": "MITRE ATT&CK Mapping",
    "containment": "Containment",
    "recovery": "Recovery",
    "recommendations": "Recommendations",
    "appendix": "Appendix",
}


@dataclass
class ReportSection:
    """One section of a report."""
    kind: str = ""
    title: str = ""
    content: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)
    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    """In-memory report — NOT an ORM model."""
    id: int | None = None
    student_id: int | None = None
    scenario_id: int | None = None
    report_type: str = "lab"
    title: str = ""
    summary: str = ""
    sections: list[ReportSection] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    mitre_mapping: list[dict[str, str]] = field(default_factory=list)
    score: float = 0.0
    grade: str = ""
    xp: int = 0
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def section_by_kind(self, kind: str) -> ReportSection | None:
        for s in self.sections:
            if s.kind == kind:
                return s
        return None
