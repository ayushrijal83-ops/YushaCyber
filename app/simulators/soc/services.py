"""SOC services — orchestrate the queue → case handoff.

Thin façade that keeps the simulator small: it asks ``load_alert_case``
for the forensics case to render when the analyst opens an alert, and
``load_alert_context`` to hydrate the whole workspace with the queue
plus the currently-open alert's playbook, checklist and case.
"""

from __future__ import annotations

from typing import Any

from app.labs.forensics.engine import case_from_orm
from app.labs.forensics.models import ForensicsCase
from app.simulators.soc.alerts import (
    alert_to_dict,
    find_by_code,
    open_queue,
    resolved_queue,
)
from app.simulators.soc.dashboard import dashboard_stats, recent_activity
from app.simulators.soc.models import (
    SocAlert,
    SocChecklistItem,
    SocPlaybook,
)
from app.simulators.soc.playbooks import playbook_view


def all_alerts() -> list[SocAlert]:
    return SocAlert.query.order_by(SocAlert.at_time.desc()).all()


def load_alert_case(alert_code: str) -> dict[str, Any] | None:
    """Return the forensics case dict for an alert, or None."""
    alert = SocAlert.query.filter_by(alert_code=alert_code).first()
    if alert is None or alert.case_id is None:
        return None
    case = ForensicsCase.query.get(alert.case_id)
    if case is None:
        return None
    return case_from_orm(case)


def playbook_for(alert_type: str) -> dict[str, Any]:
    playbook = SocPlaybook.query.filter_by(alert_type=alert_type).first()
    return playbook_view(playbook)


def all_playbook_options() -> list[dict[str, Any]]:
    """Every seeded playbook, for the picker dropdown. Playbooks are
    keyed by ``alert_type`` (unique in the schema) — that's the value
    the ``select_playbook`` action expects."""
    return [
        {"alert_type": p.alert_type, "title": p.title,
         "summary": p.summary or ""}
        for p in SocPlaybook.query.order_by(SocPlaybook.title).all()
    ]


def checklist_for(case_id: int | None) -> list[dict[str, Any]]:
    if case_id is None:
        return []
    items = (SocChecklistItem.query
             .filter_by(case_id=case_id)
             .order_by(SocChecklistItem.display_order).all())
    return [
        {"slug": item.slug, "text": item.text,
         "is_required": item.is_required,
         "display_order": item.display_order}
        for item in items
    ]


def workspace_context(active_alert_code: str | None) -> dict[str, Any]:
    """Build the whole SOC workspace context in one call.

    Bundles: dashboard stats, open/resolved queues, recent activity,
    plus (when an alert is opened) its dict, playbook view, checklist,
    and underlying forensics case.
    """
    alerts = all_alerts()
    ctx = {
        "stats": dashboard_stats(alerts),
        "open_queue": open_queue(alerts),
        "resolved_queue": resolved_queue(alerts),
        "recent_activity": recent_activity(alerts),
        "active_alert": None,
        "active_case": None,
        "playbook": playbook_view(None),
        "checklist": [],
    }
    if not active_alert_code:
        return ctx
    alert = find_by_code(alerts, active_alert_code)
    if alert is None:
        return ctx
    ctx["active_alert"] = alert_to_dict(alert)
    ctx["playbook"] = playbook_for(alert.alert_type)
    ctx["checklist"] = checklist_for(alert.case_id)
    if alert.case_id is not None:
        case = ForensicsCase.query.get(alert.case_id)
        if case is not None:
            ctx["active_case"] = case_from_orm(case)
    return ctx
