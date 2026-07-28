"""Report builder — fluent API for constructing reports section by section.

    report = (ReportBuilder("Investigation Report")
              .set_type("investigation")
              .add_executive_summary("A breach was detected...")
              .add_timeline([{"at": "02:00", "event": "VPN login"}])
              .add_evidence([{"ref": "dns-log", "label": "DNS capture"}])
              .add_findings([{"finding": "C2 domain identified"}])
              .add_mitre([{"technique_id": "T1059.001", ...}])
              .add_recommendations(["Enable MFA", "Block C2 IPs"])
              .build())
"""

from __future__ import annotations

from typing import Any

from app.core.report.types import Report, ReportSection, SECTION_LABELS


class ReportBuilder:
    """Fluent builder for Report objects."""

    def __init__(self, title: str = "Report") -> None:
        self._title = title
        self._type = "lab"
        self._student_id: int | None = None
        self._scenario_id: int | None = None
        self._sections: list[ReportSection] = []
        self._findings: list[dict[str, Any]] = []
        self._evidence: list[dict[str, Any]] = []
        self._timeline: list[dict[str, Any]] = []
        self._recommendations: list[str] = []
        self._mitre: list[dict[str, str]] = []
        self._score: float = 0.0
        self._grade: str = ""
        self._xp: int = 0
        self._order = 0

    def set_type(self, report_type: str) -> "ReportBuilder":
        self._type = report_type
        return self

    def set_student(self, student_id: int) -> "ReportBuilder":
        self._student_id = student_id
        return self

    def set_scenario(self, scenario_id: int) -> "ReportBuilder":
        self._scenario_id = scenario_id
        return self

    def set_score(self, score: float, grade: str = "",
                  xp: int = 0) -> "ReportBuilder":
        self._score = score
        self._grade = grade
        self._xp = xp
        return self

    def _next_order(self) -> int:
        self._order += 1
        return self._order

    def add_section(self, kind: str, content: str = "",
                    items: list[dict[str, Any]] | None = None,
                    title: str | None = None) -> "ReportBuilder":
        self._sections.append(ReportSection(
            kind=kind,
            title=title or SECTION_LABELS.get(kind, kind),
            content=content,
            items=items or [],
            order=self._next_order()))
        return self

    def add_executive_summary(self, text: str) -> "ReportBuilder":
        return self.add_section("executive_summary", content=text)

    def add_objectives(self,
                       items: list[dict[str, Any]]) -> "ReportBuilder":
        return self.add_section("objectives", items=items)

    def add_timeline(self,
                     events: list[dict[str, Any]]) -> "ReportBuilder":
        self._timeline = events
        return self.add_section("timeline", items=events)

    def add_evidence(self,
                     items: list[dict[str, Any]]) -> "ReportBuilder":
        self._evidence = items
        return self.add_section("evidence", items=items)

    def add_findings(self,
                     items: list[dict[str, Any]]) -> "ReportBuilder":
        self._findings = items
        return self.add_section("findings", items=items)

    def add_root_cause(self, text: str) -> "ReportBuilder":
        return self.add_section("root_cause", content=text)

    def add_mitre(self,
                  techniques: list[dict[str, str]]) -> "ReportBuilder":
        self._mitre = techniques
        return self.add_section("mitre", items=techniques)

    def add_containment(self, text: str) -> "ReportBuilder":
        return self.add_section("containment", content=text)

    def add_recovery(self, text: str) -> "ReportBuilder":
        return self.add_section("recovery", content=text)

    def add_recommendations(self, items: list[str]) -> "ReportBuilder":
        self._recommendations = items
        return self.add_section("recommendations",
                                items=[{"text": r} for r in items])

    def add_appendix(self, content: str = "",
                     items: list[dict[str, Any]] | None = None
                     ) -> "ReportBuilder":
        return self.add_section("appendix", content=content,
                                items=items)

    def build(self) -> Report:
        return Report(
            student_id=self._student_id,
            scenario_id=self._scenario_id,
            report_type=self._type,
            title=self._title,
            summary=(self._sections[0].content[:300]
                     if self._sections else ""),
            sections=list(self._sections),
            findings=self._findings,
            evidence=self._evidence,
            timeline=self._timeline,
            recommendations=self._recommendations,
            mitre_mapping=self._mitre,
            score=self._score,
            grade=self._grade,
            xp=self._xp,
        )
