"""Report models — builders from existing data structures.

These are factory functions, not ORM models. They construct Report
dataclasses from Lab/SOC/Forensics data.
"""

from __future__ import annotations

from typing import Any

from app.core.report.types import Report, ReportSection


def report_from_dict(data: dict[str, Any]) -> Report:
    """Build a Report from a plain dict."""
    sections = []
    for s in data.get("sections") or []:
        sections.append(ReportSection(
            kind=s.get("kind", ""),
            title=s.get("title", ""),
            content=s.get("content", ""),
            items=s.get("items", []),
            order=s.get("order", 0)))
    return Report(
        id=data.get("id"),
        student_id=data.get("student_id"),
        scenario_id=data.get("scenario_id"),
        report_type=data.get("report_type", "lab"),
        title=data.get("title", ""),
        summary=data.get("summary", ""),
        sections=sections,
        findings=data.get("findings", []),
        evidence=data.get("evidence", []),
        timeline=data.get("timeline", []),
        recommendations=data.get("recommendations", []),
        mitre_mapping=data.get("mitre_mapping", []),
        score=data.get("score", 0.0),
        grade=data.get("grade", ""),
        xp=data.get("xp", 0),
        created_at=data.get("created_at", ""),
    )


def report_from_state(state: dict[str, Any],
                      report_type: str = "investigation",
                      title: str = "") -> Report:
    """Build a Report from a simulator session state dict.

    Pulls report text, score, timeline, evidence, MITRE mapping
    from the SOC/forensics session state — backward-compatible
    with every existing report-submission action.
    """
    report_text = state.get("report") or ""
    score_data = (state.get("ir_score")
                  or state.get("hunt_report")
                  or state.get("assessment_score")
                  or {})
    sections = []
    if report_text:
        sections.append(ReportSection(
            kind="executive_summary",
            title="Executive Summary",
            content=report_text,
            order=1))
    mitre = []
    for tid in state.get("hunt_mitre_mapped") or []:
        mitre.append({"technique_id": tid})
    timeline = []
    forensics = state.get("forensics") or {}
    case = forensics.get("case") or {}
    for evt in case.get("timeline") or []:
        timeline.append(evt)
    evidence = []
    for bm in state.get("hunt_bookmarks") or []:
        evidence.append(bm)

    return Report(
        report_type=report_type,
        title=title or f"{report_type.replace('_', ' ').title()} Report",
        summary=report_text[:300] if report_text else "",
        sections=sections,
        timeline=timeline,
        evidence=evidence,
        mitre_mapping=mitre,
        score=score_data.get("total", 0),
        grade=score_data.get("rating") or score_data.get("grade", ""),
        xp=0,
    )
