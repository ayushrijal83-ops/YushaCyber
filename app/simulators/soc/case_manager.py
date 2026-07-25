"""SOC Case Management engine (YC-030.3.5).

Pure helpers that operate on ``SocCase`` ORM rows. Every future SOC
investigation scenario (alert triage, IR, threat hunting) uses this
layer to create, query and close cases.
"""

from __future__ import annotations

from typing import Any

from app.extensions import db
from app.simulators.soc.models import SocCase, SocCaseNote


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------
def case_to_dict(case: SocCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "case_code": case.case_code,
        "title": case.title,
        "status": case.status,
        "severity": case.severity,
        "assigned_analyst": case.assigned_analyst or "",
        "created_at": str(case.created_at) if case.created_at else "",
        "updated_at": str(case.updated_at) if case.updated_at else "",
        "closed_at": case.closed_at or "",
        "linked_alerts": case.get_linked_alerts(),
        "linked_evidence": case.get_linked_evidence(),
        "progress": case.progress,
        "notes": [
            {"id": n.id, "author": n.author, "text": n.text,
             "created_at": str(n.created_at) if n.created_at else ""}
            for n in (case.notes or [])
        ],
    }


# ---------------------------------------------------------------------------
# Dashboard queries
# ---------------------------------------------------------------------------
def dashboard_stats() -> dict[str, int]:
    """Aggregate case counts for the SOC dashboard."""
    all_cases = SocCase.query.all()
    open_statuses = {"new", "in_progress", "escalated"}
    return {
        "total": len(all_cases),
        "open": sum(1 for c in all_cases if c.status in open_statuses),
        "assigned": sum(1 for c in all_cases
                        if c.assigned_analyst and c.status in open_statuses),
        "critical": sum(1 for c in all_cases
                        if c.severity == "critical"
                        and c.status in open_statuses),
        "resolved": sum(1 for c in all_cases
                        if c.status in ("resolved", "closed")),
    }


def open_cases() -> list[dict[str, Any]]:
    return [case_to_dict(c) for c in
            SocCase.query.filter(
                SocCase.status.in_(("new", "in_progress", "escalated")))
            .order_by(SocCase.severity, SocCase.created_at).all()]


def recently_closed(limit: int = 10) -> list[dict[str, Any]]:
    return [case_to_dict(c) for c in
            SocCase.query.filter(
                SocCase.status.in_(("resolved", "closed")))
            .order_by(SocCase.updated_at.desc())
            .limit(limit).all()]


def assigned_to(analyst: str) -> list[dict[str, Any]]:
    return [case_to_dict(c) for c in
            SocCase.query.filter_by(assigned_analyst=analyst)
            .order_by(SocCase.severity, SocCase.created_at).all()]


def case_timeline(case: SocCase) -> list[dict[str, Any]]:
    """Build a timeline from notes + status changes."""
    events: list[dict[str, Any]] = []
    events.append({
        "at": str(case.created_at) if case.created_at else "",
        "type": "created",
        "text": f"Case {case.case_code} created.",
    })
    for note in case.notes or []:
        events.append({
            "at": str(note.created_at) if note.created_at else "",
            "type": "note",
            "text": f"[{note.author}] {note.text}",
        })
    if case.closed_at:
        events.append({
            "at": case.closed_at,
            "type": "closed",
            "text": f"Case closed ({case.status}).",
        })
    events.sort(key=lambda e: e.get("at") or "")
    return events


# ---------------------------------------------------------------------------
# Mutations (called from simulator actions)
# ---------------------------------------------------------------------------
def create_case(case_code: str, title: str,
                severity: str = "medium",
                linked_alerts: list[str] | None = None) -> SocCase:
    existing = SocCase.query.filter_by(case_code=case_code).first()
    if existing:
        return existing
    case = SocCase(case_code=case_code, title=title,
                   severity=severity, status="new")
    if linked_alerts:
        case.set_linked_alerts(linked_alerts)
    db.session.add(case)
    db.session.flush()
    return case


def assign_case(case: SocCase, analyst: str) -> None:
    case.assigned_analyst = analyst
    if case.status == "new":
        case.status = "in_progress"
    db.session.flush()


def add_note(case: SocCase, author: str, text: str) -> SocCaseNote:
    note = SocCaseNote(soc_case_id=case.id, author=author, text=text)
    db.session.add(note)
    db.session.flush()
    return note


def link_alert(case: SocCase, alert_code: str) -> None:
    codes = case.get_linked_alerts()
    if alert_code not in codes:
        codes.append(alert_code)
        case.set_linked_alerts(codes)
        db.session.flush()


def link_evidence(case: SocCase, evidence_ref: str) -> None:
    items = case.get_linked_evidence()
    if evidence_ref not in items:
        items.append(evidence_ref)
        case.set_linked_evidence(items)
        db.session.flush()


def escalate_case(case: SocCase) -> None:
    case.status = "escalated"
    db.session.flush()


def close_case(case: SocCase, closed_at: str | None = None) -> None:
    case.status = "closed"
    case.closed_at = closed_at or ""
    case.progress = 100
    db.session.flush()


def update_progress(case: SocCase, progress: int) -> None:
    case.progress = max(0, min(100, progress))
    db.session.flush()


def find_by_code(case_code: str) -> SocCase | None:
    return SocCase.query.filter_by(case_code=case_code).first()
