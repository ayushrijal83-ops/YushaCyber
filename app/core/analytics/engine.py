"""Analytics engine — insight generation and export helpers."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.core.analytics.types import Insight, StudentMetrics


# ---------------------------------------------------------------------------
# Insight generation
# ---------------------------------------------------------------------------
INSIGHT_RULES: list[dict[str, Any]] = [
    {"key": "completion_rate", "op": "<", "threshold": 0.3,
     "severity": "warning",
     "message": "{username} has a low completion rate ({completion_rate:.0%})."},
    {"key": "completion_rate", "op": ">=", "threshold": 0.9,
     "severity": "success",
     "message": "{username} has an excellent completion rate ({completion_rate:.0%})."},
    {"key": "hints_used", "op": ">", "threshold": 20,
     "severity": "info",
     "message": "{username} frequently requests hints ({hints_used} used)."},
    {"key": "average_time_seconds", "op": "<", "threshold": 300,
     "severity": "success",
     "message": "{username} completes labs quickly (avg {average_time_seconds}s)."},
    {"key": "perfect_scores", "op": ">", "threshold": 5,
     "severity": "success",
     "message": "{username} has {perfect_scores} perfect scores."},
    {"key": "current_streak", "op": ">=", "threshold": 7,
     "severity": "success",
     "message": "{username} is on a {current_streak}-day streak!"},
]


def generate_insights(student: StudentMetrics) -> list[Insight]:
    """Generate automatic learning insights for a student."""
    insights: list[Insight] = []
    data = student.to_dict()
    for rule in INSIGHT_RULES:
        value = data.get(rule["key"], 0)
        threshold = rule["threshold"]
        triggered = False
        if rule["op"] == "<" and value < threshold:
            triggered = True
        elif rule["op"] == ">" and value > threshold:
            triggered = True
        elif rule["op"] == ">=" and value >= threshold:
            triggered = True
        elif rule["op"] == "<=" and value <= threshold:
            triggered = True
        if triggered:
            insights.append(Insight(
                category="student",
                severity=rule["severity"],
                message=rule["message"].format(**data),
                metric_key=rule["key"],
                metric_value=float(value),
            ))
    return insights


def generate_track_insights(
        track_data: dict[str, Any]) -> list[Insight]:
    """Insights for a track (e.g. high failure rate)."""
    insights: list[Insight] = []
    pct = track_data.get("completion_pct", 1.0)
    name = track_data.get("track_name", "Track")
    if pct < 0.3:
        insights.append(Insight(
            category="track", severity="warning",
            message=f"{name} has a low completion rate ({pct:.0%}).",
            metric_key="completion_pct", metric_value=pct))
    if pct >= 0.9:
        insights.append(Insight(
            category="track", severity="success",
            message=f"{name} has an excellent completion rate ({pct:.0%}).",
            metric_key="completion_pct", metric_value=pct))
    return insights


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_json(data: Any) -> str:
    """Export analytics data as JSON."""
    if hasattr(data, "to_dict"):
        data = data.to_dict()
    return json.dumps(data, indent=2, default=str)


def export_csv(rows: list[dict[str, Any]],
               fieldnames: list[str] | None = None) -> str:
    """Export a list of dicts as CSV."""
    if not rows:
        return ""
    fieldnames = fieldnames or list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames,
                            extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()
