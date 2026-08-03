"""AI analytics export — CSV and JSON output."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.core.ai.analytics.engine import get_dashboard


def export_json(dataset: str = "all") -> str:
    """Export analytics as JSON."""
    d = get_dashboard()
    if dataset == "all":
        return json.dumps(d.to_dict(), indent=2, default=str)
    section = getattr(d, dataset, None)
    if section and hasattr(section, "to_dict"):
        return json.dumps(section.to_dict(), indent=2, default=str)
    return json.dumps({"error": f"Unknown dataset: {dataset}"})


def export_csv(dataset: str = "students") -> str:
    """Export a flat dataset as CSV."""
    d = get_dashboard()
    rows: list[dict[str, Any]] = []
    if dataset == "ai_usage":
        rows = [d.ai_usage.to_dict()]
    elif dataset == "students":
        rows = [d.students.to_dict()]
    elif dataset == "hints":
        rows = [d.hints.to_dict()]
    elif dataset == "labs":
        rows = [d.labs.to_dict()]
    elif dataset == "recommendations":
        rows = [d.recommendations.to_dict()]
    elif dataset == "health":
        rows = [d.health.to_dict()]
    else:
        return ""
    if not rows:
        return ""
    # Flatten nested dicts for CSV.
    flat_rows = []
    for row in rows:
        flat: dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, (list, dict)):
                flat[k] = json.dumps(v, default=str)
            else:
                flat[k] = v
        flat_rows.append(flat)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(flat_rows[0].keys()),
                            extrasaction="ignore")
    writer.writeheader()
    for r in flat_rows:
        writer.writerow(r)
    return buf.getvalue()
