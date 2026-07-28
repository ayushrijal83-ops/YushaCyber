"""Report services — the public API.

Every module calls these functions instead of reaching into
submodules directly.
"""

from __future__ import annotations

from typing import Any

from app.core.report.builder import ReportBuilder
from app.core.report.export import export_html, export_json, export_markdown
from app.core.report.renderer import render
from app.core.report.types import Report


def create_report(title: str = "Report",
                  report_type: str = "lab",
                  student_id: int | None = None,
                  scenario_id: int | None = None) -> Report:
    """Create an empty report with metadata."""
    from datetime import datetime, timezone
    return Report(
        student_id=student_id,
        scenario_id=scenario_id,
        report_type=report_type,
        title=title,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def build_report(title: str = "Report",
                 report_type: str = "lab",
                 **kwargs: Any) -> ReportBuilder:
    """Return a ReportBuilder pre-configured for the given type.

    Usage::

        report = (build_report("Investigation", "investigation")
                  .add_executive_summary("...")
                  .add_timeline([...])
                  .build())
    """
    return (ReportBuilder(title)
            .set_type(report_type)
            .set_student(kwargs.get("student_id") or 0)
            .set_scenario(kwargs.get("scenario_id") or 0))


def render_report(report: Report,
                  fmt: str = "markdown") -> str:
    """Render a report to the specified format string."""
    return render(report, fmt)


def export_report(report: Report, fmt: str = "markdown") -> str:
    """Export a report (alias for render_report)."""
    if fmt == "html":
        return export_html(report)
    if fmt == "json":
        return export_json(report)
    return export_markdown(report)


def report_summary(report: Report) -> dict[str, Any]:
    """Return a summary dict for display."""
    return {
        "title": report.title,
        "type": report.report_type,
        "grade": report.grade,
        "score": report.score,
        "xp": report.xp,
        "sections": len(report.sections),
        "findings": len(report.findings),
        "evidence": len(report.evidence),
        "timeline": len(report.timeline),
        "mitre": len(report.mitre_mapping),
        "recommendations": len(report.recommendations),
    }
