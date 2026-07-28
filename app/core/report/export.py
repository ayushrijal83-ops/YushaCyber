"""Report export — convenience wrappers for each output format."""

from __future__ import annotations

from app.core.report.renderer import render
from app.core.report.types import OutputFormat, Report


def export_html(report: Report) -> str:
    """Export a report as an HTML fragment."""
    return render(report, OutputFormat.HTML)


def export_markdown(report: Report) -> str:
    """Export a report as Markdown."""
    return render(report, OutputFormat.MARKDOWN)


def export_json(report: Report) -> str:
    """Export a report as a JSON string."""
    return render(report, OutputFormat.JSON)
