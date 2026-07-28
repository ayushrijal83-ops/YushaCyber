"""Report renderer — converts Report objects to output formats.

Supports HTML, Markdown, and JSON. Designed so PDF can be added
later by adding a ``render_pdf()`` function that takes the same
Report input.
"""

from __future__ import annotations

import json

from app.core.report.types import (
    OutputFormat,
    Report,
)


def render(report: Report,
           fmt: OutputFormat | str = OutputFormat.MARKDOWN
           ) -> str:
    """Render a report to the specified format."""
    fmt = OutputFormat(fmt) if isinstance(fmt, str) else fmt
    if fmt == OutputFormat.HTML:
        return render_html(report)
    if fmt == OutputFormat.JSON:
        return render_json(report)
    return render_markdown(report)


def render_markdown(report: Report) -> str:
    """Render to Markdown."""
    lines: list[str] = []
    lines.append(f"# {report.title}")
    lines.append("")
    if report.grade:
        lines.append(f"**Grade:** {report.grade}  ")
    if report.score:
        lines.append(f"**Score:** {report.score}  ")
    if report.xp:
        lines.append(f"**XP Earned:** {report.xp}  ")
    if report.grade or report.score:
        lines.append("")

    for section in sorted(report.sections, key=lambda s: s.order):
        lines.append(f"## {section.title}")
        lines.append("")
        if section.content:
            lines.append(section.content)
            lines.append("")
        for item in section.items:
            if isinstance(item, dict):
                parts = [f"{k}: {v}" for k, v in item.items()
                         if v and k != "order"]
                lines.append(f"- {', '.join(parts)}")
            else:
                lines.append(f"- {item}")
        if section.items:
            lines.append("")
    return "\n".join(lines)


def render_html(report: Report) -> str:
    """Render to HTML fragment (no <html>/<body> wrapper)."""
    parts: list[str] = []
    parts.append('<article class="report">')
    parts.append(f'<h1>{_esc(report.title)}</h1>')
    if report.grade or report.score:
        parts.append('<div class="report-meta">')
        if report.grade:
            parts.append(
                f'<span class="report-grade">{_esc(report.grade)}</span>')
        if report.score:
            parts.append(
                f'<span class="report-score">{report.score}</span>')
        parts.append('</div>')

    for section in sorted(report.sections, key=lambda s: s.order):
        parts.append(f'<section class="report-section '
                     f'report-section--{_esc(section.kind)}">')
        parts.append(f'<h2>{_esc(section.title)}</h2>')
        if section.content:
            parts.append(f'<p>{_esc(section.content)}</p>')
        if section.items:
            parts.append('<ul>')
            for item in section.items:
                if isinstance(item, dict):
                    text = ", ".join(f"{k}: {v}" for k, v in item.items()
                                    if v and k != "order")
                    parts.append(f'<li>{_esc(text)}</li>')
                else:
                    parts.append(f'<li>{_esc(str(item))}</li>')
            parts.append('</ul>')
        parts.append('</section>')
    parts.append('</article>')
    return "\n".join(parts)


def render_json(report: Report) -> str:
    """Render to JSON string."""
    return json.dumps(report.to_dict(), indent=2, default=str)


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))
