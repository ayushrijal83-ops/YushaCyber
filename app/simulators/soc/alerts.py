"""Alert queue helpers.

Small pure functions that build the queue viewer, filter alerts by
status, and format one alert as a plain dict — used by both the
simulator and the SOC template.
"""

from __future__ import annotations

from typing import Any

from app.simulators.soc.dashboard import CLOSED_STATUSES, OPEN_STATUSES
from app.simulators.soc.models import SEVERITIES, SocAlert


SEVERITY_ORDER = {sev: idx for idx, sev in enumerate(SEVERITIES)}


def alert_to_dict(alert: SocAlert) -> dict[str, Any]:
    """Serialise an alert row for the queue viewer."""
    return {
        "id": alert.id,
        "alert_code": alert.alert_code,
        "title": alert.title,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "status": alert.status,
        "source": alert.source,
        "at_time": alert.at_time,
        "assigned_analyst": alert.assigned_analyst or "unassigned",
        "description": alert.description,
        "case_id": alert.case_id,
    }


def open_queue(alerts: list[SocAlert]) -> list[dict[str, Any]]:
    """Alerts still in the queue, sorted by severity then time."""
    rows = [a for a in alerts if a.status in OPEN_STATUSES]
    rows.sort(key=lambda a: (SEVERITY_ORDER.get(a.severity, 999),
                             a.at_time or ""))
    return [alert_to_dict(a) for a in rows]


def resolved_queue(alerts: list[SocAlert]) -> list[dict[str, Any]]:
    rows = [a for a in alerts if a.status in CLOSED_STATUSES]
    rows.sort(key=lambda a: a.at_time or "", reverse=True)
    return [alert_to_dict(a) for a in rows]


def find_by_code(alerts: list[SocAlert],
                 alert_code: str) -> SocAlert | None:
    for alert in alerts:
        if alert.alert_code == alert_code:
            return alert
    return None
