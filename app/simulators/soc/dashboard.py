"""SOC Analyst dashboard aggregates.

Pure functions over the SocAlert rows. Every dashboard number a real
analyst console shows — Open Alerts, per-severity counters, Resolved
Incidents, Recent Activity — comes from here so the UI never has to
compute anything itself.
"""

from __future__ import annotations

from typing import Any

from app.simulators.soc.models import SEVERITIES, SocAlert


OPEN_STATUSES = ("open", "in_progress")
CLOSED_STATUSES = ("resolved", "closed", "false_positive")


def counts_by_severity(alerts: list[SocAlert]) -> dict[str, int]:
    """Per-severity counters — only alerts still open count here."""
    out = {sev: 0 for sev in SEVERITIES}
    for alert in alerts:
        if alert.status in OPEN_STATUSES:
            out[alert.severity] = out.get(alert.severity, 0) + 1
    return out


def dashboard_stats(alerts: list[SocAlert]) -> dict[str, Any]:
    """Everything the header cards on the SOC dashboard need."""
    open_alerts = [a for a in alerts if a.status in OPEN_STATUSES]
    resolved = [a for a in alerts if a.status in CLOSED_STATUSES]
    by_sev = counts_by_severity(alerts)
    return {
        "open": len(open_alerts),
        "critical": by_sev.get("critical", 0),
        "high": by_sev.get("high", 0),
        "medium": by_sev.get("medium", 0),
        "low": by_sev.get("low", 0),
        "informational": by_sev.get("informational", 0),
        "resolved": len(resolved),
        "total": len(alerts),
    }


def recent_activity(alerts: list[SocAlert],
                    limit: int = 6) -> list[dict[str, Any]]:
    """Last N alerts sorted by ``at_time`` descending — one row per
    alert, ready to render."""
    rows = sorted(
        alerts, key=lambda a: (a.at_time or "", a.alert_code),
        reverse=True)[:limit]
    return [
        {"alert_code": a.alert_code, "title": a.title,
         "severity": a.severity, "status": a.status,
         "at_time": a.at_time, "source": a.source}
        for a in rows
    ]
