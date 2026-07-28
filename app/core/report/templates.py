"""Report templates — default section ordering per report type.

Each template defines which sections appear and in what order.
The builder can use these to pre-populate a report skeleton.
"""

from __future__ import annotations


TEMPLATES: dict[str, list[str]] = {
    "lab": [
        "executive_summary", "objectives", "findings",
        "recommendations",
    ],
    "investigation": [
        "executive_summary", "timeline", "evidence", "findings",
        "root_cause", "containment", "recovery", "recommendations",
    ],
    "threat_hunt": [
        "executive_summary", "timeline", "evidence", "findings",
        "mitre", "recommendations",
    ],
    "incident": [
        "executive_summary", "timeline", "evidence", "findings",
        "root_cause", "mitre", "containment", "recovery",
        "recommendations",
    ],
    "blue_team": [
        "executive_summary", "timeline", "evidence", "findings",
        "root_cause", "mitre", "containment", "recovery",
        "recommendations", "appendix",
    ],
    "assessment": [
        "executive_summary", "objectives", "findings",
        "recommendations",
    ],
    "completion": [
        "executive_summary", "objectives",
    ],
    "certificate_summary": [
        "executive_summary",
    ],
}


def get_template(report_type: str) -> list[str]:
    """Return the section ordering for a report type."""
    return list(TEMPLATES.get(report_type, TEMPLATES["lab"]))


def template_names() -> list[str]:
    """All available template names."""
    return sorted(TEMPLATES.keys())
