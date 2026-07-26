"""Threat Hunting engine (YC-030.6).

Provides search, IOC exploration, MITRE ATT&CK mapping, bookmark
management and hunt-report scoring. All operate on existing
ForensicsArtifact data + session state — no new tables.

Adding a new hunt = seeding artifacts with ``source_type`` values
like ``ioc_ip``, ``ioc_domain``, ``ioc_hash`` and registering a
MITRE mapping in the hunt registry. No code changes.
"""

from __future__ import annotations

from typing import Any

from app.labs.forensics.engine import ARTIFACT_SCHEMA, SOURCE_LABEL

# ---------------------------------------------------------------------------
# IOC source types (ride the generic ForensicsArtifact table).
# ---------------------------------------------------------------------------
IOC_SOURCES = (
    "ioc_ip", "ioc_domain", "ioc_hash", "ioc_filename",
    "ioc_url", "ioc_registry", "ioc_scheduled_task", "ioc_service",
)

# Extend the artifact schema so the source-viewer table renders them.

ARTIFACT_SCHEMA.update({
    "ioc_ip":             ["ip", "reputation", "geo", "first_seen"],
    "ioc_domain":         ["domain", "reputation", "registrar",
                           "first_seen"],
    "ioc_hash":           ["sha256", "filename", "verdict",
                           "first_seen"],
    "ioc_filename":       ["filename", "path", "size_bytes",
                           "verdict"],
    "ioc_url":            ["url", "category", "verdict"],
    "ioc_registry":       ["key", "value", "hive"],
    "ioc_scheduled_task": ["name", "command", "trigger", "user"],
    "ioc_service":        ["name", "binary_path", "start_type",
                           "user"],
})
SOURCE_LABEL.update({
    "ioc_ip":             "IOC — IP Addresses",
    "ioc_domain":         "IOC — Domains",
    "ioc_hash":           "IOC — File Hashes",
    "ioc_filename":       "IOC — Filenames",
    "ioc_url":            "IOC — URLs",
    "ioc_registry":       "IOC — Registry Keys",
    "ioc_scheduled_task": "IOC — Scheduled Tasks",
    "ioc_service":        "IOC — Services",
})


# ---------------------------------------------------------------------------
# MITRE ATT&CK technique registry.
# ---------------------------------------------------------------------------
MITRE_TACTICS = (
    "initial_access", "execution", "persistence",
    "privilege_escalation", "defense_evasion", "credential_access",
    "discovery", "lateral_movement", "collection",
    "exfiltration", "impact",
)

TACTIC_LABELS = {
    "initial_access": "Initial Access",
    "execution": "Execution",
    "persistence": "Persistence",
    "privilege_escalation": "Privilege Escalation",
    "defense_evasion": "Defense Evasion",
    "credential_access": "Credential Access",
    "discovery": "Discovery",
    "lateral_movement": "Lateral Movement",
    "collection": "Collection",
    "exfiltration": "Exfiltration",
    "impact": "Impact",
}

# Hunt-code → list of {tactic, technique_id, technique_name, evidence_ref}
_MITRE_MAPPINGS: dict[str, list[dict[str, str]]] = {}


def register_mitre(hunt_code: str,
                   mappings: list[dict[str, str]]) -> None:
    _MITRE_MAPPINGS[hunt_code] = mappings


def get_mitre(hunt_code: str) -> list[dict[str, str]]:
    return _MITRE_MAPPINGS.get(hunt_code, [])


def mitre_summary(hunt_code: str) -> list[dict[str, Any]]:
    """Group MITRE techniques by tactic for display."""
    mappings = get_mitre(hunt_code)
    grouped: dict[str, list[dict[str, str]]] = {}
    for m in mappings:
        grouped.setdefault(m.get("tactic", ""), []).append(m)
    return [
        {"tactic": t, "label": TACTIC_LABELS.get(t, t),
         "techniques": grouped.get(t, [])}
        for t in MITRE_TACTICS if t in grouped
    ]


# ---------------------------------------------------------------------------
# Telemetry search — filters artifacts by field value.
# ---------------------------------------------------------------------------
def search_telemetry(artifacts: list[dict[str, Any]],
                     query: str,
                     field: str | None = None) -> list[dict[str, Any]]:
    """Search artifacts by a query string. If ``field`` is given,
    only match that data key; otherwise match any field."""
    query = (query or "").strip().lower()
    if not query:
        return []
    results = []
    for artifact in artifacts:
        data = artifact.get("data") or {}
        if field:
            value = str(data.get(field) or "").lower()
            if query in value:
                results.append(artifact)
        else:
            # Search all string values in the artifact.
            matched = False
            for v in data.values():
                if query in str(v).lower():
                    matched = True
                    break
            if not matched:
                # Also check at_time and source_type.
                if (query in str(artifact.get("at_time") or "").lower()
                        or query in str(
                            artifact.get("source_type") or "").lower()):
                    matched = True
            if matched:
                results.append(artifact)
    return results


def ioc_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to just IOC-typed artifacts."""
    return [a for a in artifacts
            if (a.get("source_type") or "").startswith("ioc_")]


def related_evidence(artifacts: list[dict[str, Any]],
                     ioc_value: str) -> list[dict[str, Any]]:
    """Find every artifact that references an IOC value."""
    ioc_value = (ioc_value or "").strip().lower()
    if not ioc_value:
        return []
    return [a for a in artifacts
            if any(ioc_value in str(v).lower()
                   for v in (a.get("data") or {}).values())]


# ---------------------------------------------------------------------------
# Bookmarks (session-state helpers).
# ---------------------------------------------------------------------------
def add_bookmark(state: dict[str, Any],
                 ref: str, label: str) -> dict[str, Any]:
    bookmarks = list(state.get("hunt_bookmarks") or [])
    if not any(b.get("ref") == ref for b in bookmarks):
        bookmarks.append({"ref": ref, "label": label[:200]})
    state["hunt_bookmarks"] = bookmarks
    return state


def remove_bookmark(state: dict[str, Any],
                    ref: str) -> dict[str, Any]:
    bookmarks = [b for b in (state.get("hunt_bookmarks") or [])
                 if b.get("ref") != ref]
    state["hunt_bookmarks"] = bookmarks
    return state


# ---------------------------------------------------------------------------
# Structured investigation notes (session-state).
# ---------------------------------------------------------------------------
def add_hunt_note(state: dict[str, Any],
                  note: dict[str, str]) -> dict[str, Any]:
    notes = list(state.get("hunt_notes") or [])
    notes.append({
        "title": (note.get("title") or "")[:120],
        "observation": (note.get("observation") or "")[:500],
        "evidence": (note.get("evidence") or "")[:200],
        "priority": (note.get("priority") or "medium")[:20],
        "recommendation": (note.get("recommendation") or "")[:300],
    })
    state["hunt_notes"] = notes
    return state


# ---------------------------------------------------------------------------
# Hunt report scoring.
# ---------------------------------------------------------------------------
HUNT_REPORT_SECTIONS = (
    "executive summary", "hypothesis", "evidence",
    "findings", "mitre", "recommendations",
)


def score_hunt_report(report: str,
                      iocs_found: int,
                      mitre_mapped: int,
                      bookmarks_count: int,
                      hints_used: int = 0) -> dict[str, Any]:
    """Grade a hunt report."""
    text = (report or "").strip().lower()
    length_ok = len(text) >= 150
    sections_hit = sum(1 for s in HUNT_REPORT_SECTIONS if s in text)

    ioc_score = min(20, iocs_found * 4)
    mitre_score = min(20, mitre_mapped * 4)
    evidence_score = min(10, bookmarks_count * 2)
    report_score = min(30, sections_hit * 5 + (10 if length_ok else 0))
    hint_penalty = hints_used * 5

    total = max(0, ioc_score + mitre_score + evidence_score
                + report_score - hint_penalty)
    max_score = 80  # 20 IOC + 20 MITRE + 10 evidence + 30 report

    ratio = total / max(1, max_score)
    if ratio >= 0.9:
        rating = "Excellent"
    elif ratio >= 0.75:
        rating = "Good"
    elif ratio >= 0.5:
        rating = "Pass"
    else:
        rating = "Fail"

    return {
        "total": total, "max": max_score,
        "ratio": round(ratio, 2), "rating": rating,
        "breakdown": {
            "ioc": ioc_score, "mitre": mitre_score,
            "evidence": evidence_score, "report": report_score,
            "hints": hint_penalty,
        },
    }
