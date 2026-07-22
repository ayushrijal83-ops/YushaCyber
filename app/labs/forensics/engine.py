"""Digital Forensics engine (YC-029.5.2).

Pure functions over case dicts — no DB, no I/O, no execution. Handed a
case definition, produces the workstation view (evidence sidebar,
metadata panel, timeline) plus deterministic simulated hashes and the
findings validator.

Simulated hashes are not real MD5/SHA-256 digests. They are stable,
deterministic strings derived from the evidence slug so students see
plausible-looking artefacts they can compare — every metadata panel
shows the same value, and the same submission always evaluates the
same way. No hashing library is required.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


# Alphabets used to stretch a short input into hex-shaped strings the
# way real MD5/SHA-256 outputs look — sourced from a keyed digest of the
# evidence slug so students see stable, plausible values.
def _hex_of(seed: str, length: int) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    while len(digest) < length:
        digest += hashlib.sha256(digest.encode("utf-8")).hexdigest()
    return digest[:length]


def simulated_hash(evidence_slug: str, algorithm: str) -> str:
    """Deterministic simulated hash for a piece of evidence.

    ``algorithm`` is "md5" or "sha256"; anything else falls back to
    sha256 length. The result is derived by SHA-256'ing a namespaced
    seed and truncating — repeatable but not a real hash of file content
    (there IS no file content in this simulation).
    """
    algorithm = (algorithm or "sha256").lower()
    length = 32 if algorithm == "md5" else 64
    return _hex_of(f"yc:forensics:{evidence_slug}:{algorithm}", length)


# ===========================================================================
# View builders
# ===========================================================================
@dataclass
class Metadata:
    """The metadata panel for one evidence item."""
    filename: str
    extension: str
    owner: str
    created: str
    modified: str
    size: str
    md5: str
    sha256: str
    notes: str


def format_size(nbytes: int) -> str:
    """Human file size — bytes → KB/MB with 1 decimal."""
    n = int(nbytes or 0)
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def evidence_metadata(evidence: dict[str, Any]) -> Metadata:
    """Metadata panel for one evidence dict."""
    slug = evidence["slug"]
    return Metadata(
        filename=evidence["filename"],
        extension=evidence.get("extension") or "",
        owner=evidence.get("owner") or "user",
        created=evidence.get("created_at_display") or "—",
        modified=evidence.get("modified_at_display") or "—",
        size=format_size(evidence.get("size_bytes") or 0),
        md5=simulated_hash(slug, "md5"),
        sha256=simulated_hash(slug, "sha256"),
        notes=evidence.get("notes") or "",
    )


def build_view(case: dict[str, Any]) -> dict[str, Any]:
    """Turn a case dict into the workstation view for the UI."""
    evidence = list(case.get("evidence") or [])
    evidence.sort(key=lambda e: (e.get("display_order") or 0,
                                 e.get("slug") or ""))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        grouped.setdefault(item["kind"], []).append(item)

    return {
        "case_title": case.get("title") or "Forensics case",
        "workstation": case.get("workstation_name") or "WORKSTATION-01",
        "investigator": case.get("investigator") or "Investigator",
        "briefing": case.get("briefing") or "",
        "evidence": evidence,
        "grouped": grouped,
        "timeline": list(case.get("timeline") or []),
    }


# ===========================================================================
# Findings validation
# ===========================================================================
@dataclass
class Finding:
    """A single field the student submits."""
    key: str
    value: str


def find_by_slug(case: dict[str, Any],
                 slug: str) -> dict[str, Any] | None:
    for item in case.get("evidence") or []:
        if item.get("slug") == slug:
            return item
    return None


def evaluate_findings(case: dict[str, Any],
                      findings: dict[str, str]) -> dict[str, Any]:
    """Grade a submission against a case's ground truth.

    findings keys:
      modified_slug     — slug of the file that was modified
      modified_hash     — sha256 of that file (from the panel)
      modified_time     — HH:MM the timeline shows for the modification
      suspicious_slug   — slug of the suspicious artefact

    Returns a dict of per-check booleans plus ``all_correct``.
    """
    modified = next(
        (e for e in case.get("evidence") or []
         if e.get("is_modified")), None)
    suspicious = next(
        (e for e in case.get("evidence") or []
         if e.get("is_suspicious")), None)
    modified_slug = modified["slug"] if modified else ""
    suspicious_slug = suspicious["slug"] if suspicious else ""

    expected_hash = simulated_hash(modified_slug, "sha256") \
        if modified_slug else ""

    modified_time = ""
    for event in case.get("timeline") or []:
        if (event.get("kind") == "file_modified"
                and event.get("evidence_slug") == modified_slug):
            modified_time = event.get("at_time") or ""
            break

    def _match(user: str, expected: str) -> bool:
        return (user or "").strip().lower() == (expected or "").strip().lower()

    checks = {
        "modified_slug": _match(findings.get("modified_slug", ""),
                                modified_slug),
        "modified_hash": _match(findings.get("modified_hash", ""),
                                expected_hash),
        "modified_time": _match(findings.get("modified_time", ""),
                                modified_time),
        "suspicious_slug": _match(findings.get("suspicious_slug", ""),
                                  suspicious_slug),
    }
    checks["all_correct"] = all(checks.values())
    return checks


# ===========================================================================
# Case dict shape (used by the simulator + templates)
# ===========================================================================
def case_from_orm(case) -> dict[str, Any]:
    """Convert a ``ForensicsCase`` ORM row to the plain dict the engine
    and templates operate on — keeps the engine ORM-free."""
    return {
        "id": case.id,
        "lab_slug": case.lab_slug,
        "title": case.title,
        "briefing": case.briefing,
        "workstation_name": case.workstation_name,
        "investigator": case.investigator,
        "mode": getattr(case, "mode", "fundamentals"),
        "evidence": [
            {
                "slug": e.slug, "kind": e.kind,
                "filename": e.filename, "extension": e.extension,
                "owner": e.owner, "size_bytes": e.size_bytes,
                "created_at_display": e.created_at_display,
                "modified_at_display": e.modified_at_display,
                "notes": e.notes or "",
                "is_suspicious": e.is_suspicious,
                "is_modified": e.is_modified,
                "display_order": e.display_order,
            } for e in case.evidence
        ],
        "timeline": [
            {
                "at_time": t.at_time, "kind": t.kind,
                "description": t.description,
                "evidence_slug": t.evidence_slug,
            } for t in case.timeline
        ],
        "artifacts": artifacts_from_orm(case),
        "suspects": suspects_from_orm(case),
    }


# ===========================================================================
# Applied lab (YC-029.5.3) — artifact sources + unified timeline.
#
# Every source is a list of plain dicts (already JSON) so the engine
# stays ORM-free. Future SOC / threat-hunting / incident-response labs
# reuse this by adding a new ``source_type`` value and a schema entry.
# ===========================================================================

#: Field lists per source_type — used by the admin editor and the
#: UI viewers. Keys are label-safe. Values that end in "_time" render
#: as timestamps; everything else renders as text.
ARTIFACT_SCHEMA: dict[str, list[str]] = {
    "browser_history": ["url", "title", "visit_count"],
    "downloads":       ["filename", "url", "size_bytes"],
    "event_log":       ["event_id", "event_type", "description",
                        "user"],
    "usb_history":     ["device_name", "serial_number",
                        "connected_at", "removed_at"],
    "login_history":   ["username", "login_at", "logout_at",
                        "duration"],
    "recent_docs":     ["filename", "path", "last_accessed_at"],
}

#: Human labels for the source viewer tabs.
SOURCE_LABEL: dict[str, str] = {
    "browser_history": "Browser History",
    "downloads":       "Downloads",
    "event_log":       "Windows Event Log",
    "usb_history":     "USB Devices",
    "login_history":   "Login Sessions",
    "recent_docs":     "Recent Documents",
}


def artifacts_by_source(case: dict[str, Any],
                        source_type: str) -> list[dict[str, Any]]:
    """All artifact rows for one source, sorted by ``at_time``."""
    rows = [a for a in (case.get("artifacts") or [])
            if a.get("source_type") == source_type]
    rows.sort(key=lambda r: (r.get("sort_order") or 0,
                             r.get("at_time") or ""))
    return rows


def all_sources(case: dict[str, Any]) -> list[dict[str, Any]]:
    """Every source present in the case, with row counts and labels.
    Sorted by SOURCE_LABEL order so the UI is stable."""
    present: dict[str, int] = {}
    for a in case.get("artifacts") or []:
        source_type = a.get("source_type")
        if source_type:
            present[source_type] = present.get(source_type, 0) + 1
    return [
        {"source_type": s, "label": SOURCE_LABEL.get(s, s),
         "count": present[s]}
        for s in SOURCE_LABEL if s in present
    ]


def unified_timeline(case: dict[str, Any]) -> list[dict[str, Any]]:
    """Merge the case's own timeline events with every artifact into
    one chronologically ordered list. Each row carries a ``source`` so
    the UI can badge / colour-code it."""
    merged: list[dict[str, Any]] = []
    for event in case.get("timeline") or []:
        merged.append({
            "at_time": event.get("at_time") or "",
            "source": "timeline",
            "kind": event.get("kind") or "other",
            "description": event.get("description") or "",
            "ref": event.get("evidence_slug") or None,
        })
    for artifact in case.get("artifacts") or []:
        source = artifact.get("source_type") or "artifact"
        merged.append({
            "at_time": artifact.get("at_time") or "",
            "source": source,
            "kind": source,
            "description": _describe_artifact(artifact),
            "ref": artifact.get("id"),
        })
    merged.sort(key=lambda r: (r.get("at_time") or "",
                               r.get("source") or ""))
    return merged


def _describe_artifact(artifact: dict[str, Any]) -> str:
    """Short human summary for the unified timeline row."""
    data = artifact.get("data") or {}
    source = artifact.get("source_type") or ""
    if source == "browser_history":
        return f"Visited {data.get('title') or data.get('url') or 'page'}"
    if source == "downloads":
        return f"Downloaded {data.get('filename') or 'file'}"
    if source == "event_log":
        return (data.get("description")
                or f"Event {data.get('event_id') or ''}").strip()
    if source == "usb_history":
        return f"USB: {data.get('device_name') or 'device'}"
    if source == "login_history":
        return f"Session: {data.get('username') or 'user'}"
    if source == "recent_docs":
        return f"Opened {data.get('filename') or 'document'}"
    return artifact.get("description") or source


# ---------------------------------------------------------------------------
# Applied findings validator — 6 correlated fields.
# ---------------------------------------------------------------------------
def key_artifact(case: dict[str, Any],
                 source_type: str) -> dict[str, Any] | None:
    """Return the artifact of a source marked as the 'key' one."""
    for artifact in case.get("artifacts") or []:
        if (artifact.get("source_type") == source_type
                and artifact.get("is_key")):
            return artifact
    return None


def evaluate_applied_findings(
        case: dict[str, Any],
        findings: dict[str, str]) -> dict[str, Any]:
    """Grade the applied lab's investigation report.

    findings keys:
      first_login_time    — HH:MM of the first key login row
      usb_serial          — serial number of the rogue USB
      downloaded_filename — filename of the key download
      suspicious_url      — url of the key browser row
      timeline_first_kind — the source of the earliest merged event
      report_summary      — free-text summary; passes when non-empty
    """
    def _match(user: str, expected: str) -> bool:
        return (user or "").strip().lower() \
            == (expected or "").strip().lower()

    login = key_artifact(case, "login_history") or {}
    usb = key_artifact(case, "usb_history") or {}
    download = key_artifact(case, "downloads") or {}
    browser = key_artifact(case, "browser_history") or {}

    first_login = ((login.get("data") or {}).get("login_at")
                   or login.get("at_time") or "")
    usb_serial = (usb.get("data") or {}).get("serial_number") or ""
    dl_filename = (download.get("data") or {}).get("filename") or ""
    susp_url = (browser.get("data") or {}).get("url") or ""

    timeline = unified_timeline(case)
    first_kind = timeline[0]["source"] if timeline else ""

    report_summary = (findings.get("report_summary") or "").strip()

    checks = {
        "first_login": _match(findings.get("first_login_time", ""),
                              first_login),
        "usb_serial": _match(findings.get("usb_serial", ""),
                             usb_serial),
        "download": _match(findings.get("downloaded_filename", ""),
                           dl_filename),
        "website": _match(findings.get("suspicious_url", ""),
                          susp_url),
        "timeline": _match(findings.get("timeline_first_kind", ""),
                           first_kind),
        "report": len(report_summary) >= 40,
    }
    checks["all_correct"] = all(checks.values())
    return checks


# ---------------------------------------------------------------------------
# ORM extraction (adds artifacts + mode)
# ---------------------------------------------------------------------------
def artifacts_from_orm(case) -> list[dict[str, Any]]:
    """Convert a case's ORM artifact rows to plain dicts."""
    return [
        {
            "id": a.id, "source_type": a.source_type,
            "at_time": a.at_time, "data": a.get_data(),
            "is_key": a.is_key, "sort_order": a.sort_order,
        } for a in getattr(case, "artifacts", []) or []
    ]


# ===========================================================================
# Advanced lab (YC-029.5.4) — network evidence, suspects, correlations.
#
# Network evidence rides the generic ForensicsArtifact table with new
# source_type values ("network_dns", "network_http", …). Schema entries
# below drive the same table-viewer used by the applied lab.
# ===========================================================================

NETWORK_SOURCES = (
    "network_dns", "network_http", "network_https",
    "network_ftp", "network_smb", "network_icmp",
)

# Extend the existing schema + labels with network sources.
ARTIFACT_SCHEMA.update({
    "network_dns":   ["query", "response_ip", "domain"],
    "network_http":  ["method", "host", "path", "response_code",
                      "bytes_sent"],
    "network_https": ["host", "sni", "bytes_sent", "bytes_received"],
    "network_ftp":   ["host", "username", "operation", "filename"],
    "network_smb":   ["host", "share", "filename", "operation"],
    "network_icmp":  ["host", "message_type", "count"],
})
SOURCE_LABEL.update({
    "network_dns":   "DNS Requests",
    "network_http":  "HTTP Requests",
    "network_https": "HTTPS Sessions",
    "network_ftp":   "FTP Sessions",
    "network_smb":   "SMB Traffic",
    "network_icmp":  "ICMP Packets",
})


def network_summary(case: dict[str, Any]) -> dict[str, int]:
    """Row counts per network source — feeds the Network panel."""
    counts: dict[str, int] = {}
    for artifact in case.get("artifacts") or []:
        source = artifact.get("source_type") or ""
        if source in NETWORK_SOURCES:
            counts[source] = counts.get(source, 0) + 1
    return counts


def suspects_from_orm(case) -> list[dict[str, Any]]:
    """ORM → plain dict for suspect rows."""
    return [
        {
            "id": s.id, "slug": s.slug,
            "display_name": s.display_name,
            "role": s.role, "account": s.account,
            "notes": s.notes or "",
            "is_key": s.is_key,
            "display_order": s.display_order,
        } for s in getattr(case, "suspects", []) or []
    ]


def key_suspect(case: dict[str, Any]) -> dict[str, Any] | None:
    for suspect in case.get("suspects") or []:
        if suspect.get("is_key"):
            return suspect
    return None


# ---------------------------------------------------------------------------
# Correlation scoring.
#
# The student adds "links" — pairs of artifact ids they consider related.
# A correlation is credited when a link connects two key artifacts (the
# ones marked `is_key` in the case). This is deliberately forgiving:
# any chain that touches every key artifact via a graph of links counts
# as a full correlation.
# ---------------------------------------------------------------------------
def key_artifact_ids(case: dict[str, Any]) -> set[int]:
    return {a["id"] for a in case.get("artifacts") or []
            if a.get("is_key") and a.get("id") is not None}


def correlation_score(case: dict[str, Any],
                      links: list[list[int]]) -> dict[str, Any]:
    """How much of the key-artifact chain the student has connected."""
    key_ids = key_artifact_ids(case)
    if not key_ids:
        return {"linked": 0, "total": 0, "complete": True,
                "ratio": 1.0}
    # Union-find over key artifact ids.
    parent = {k: k for k in key_ids}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for link in links or []:
        try:
            a, b = int(link[0]), int(link[1])
        except (ValueError, TypeError, IndexError):
            continue
        if a in key_ids and b in key_ids:
            union(a, b)

    components = {find(k) for k in key_ids}
    linked_pairs = 0
    seen_pair: set[tuple[int, int]] = set()
    for link in links or []:
        try:
            a, b = int(link[0]), int(link[1])
        except (ValueError, TypeError, IndexError):
            continue
        if a in key_ids and b in key_ids and a != b:
            pair = tuple(sorted((a, b)))
            if pair not in seen_pair:
                seen_pair.add(pair)
                linked_pairs += 1
    return {
        "linked": linked_pairs,
        "total": len(key_ids),
        "complete": len(components) == 1,
        "ratio": (0.0 if not linked_pairs
                  else float(linked_pairs) / max(1, len(key_ids) - 1)),
    }


# ---------------------------------------------------------------------------
# Advanced findings validator — 6 correlated fields plus report length.
# ---------------------------------------------------------------------------
def evaluate_advanced_findings(
        case: dict[str, Any],
        findings: dict[str, str],
        links: list[list[int]] | None = None) -> dict[str, Any]:
    """Grade the advanced incident report.

    findings keys:
      compromised_account   — the key suspect's ``account`` field
      timeline_start_time   — earliest key-artifact ``at_time``
      exfiltrated_file      — filename from the key `downloads` or
                              key `network_ftp`/`network_http` row
      suspicious_ip         — response_ip from the key `network_dns`
                              row (or host from a key HTTPS row)
      attack_method         — free text; matches any of a small
                              tolerated set (case-insensitive contains)
      report_summary        — free text; passes when >= 60 chars

    ``links`` scores a bonus but is NOT required for `all_correct` —
    the correlation objective fires on its own event.
    """
    def _match(user: str, expected: str) -> bool:
        return (user or "").strip().lower() \
            == (expected or "").strip().lower()

    suspect = key_suspect(case) or {}
    download = key_artifact(case, "downloads") or {}
    dns = key_artifact(case, "network_dns") or {}

    account = suspect.get("account") or ""

    # Earliest key artifact drives the "when did it begin" answer.
    key_times = sorted(
        a.get("at_time") or ""
        for a in case.get("artifacts") or []
        if a.get("is_key"))
    timeline_start = key_times[0] if key_times else ""

    dl_filename = ((download.get("data") or {}).get("filename")
                   or "")
    suspicious_ip = ((dns.get("data") or {}).get("response_ip")
                     or "")

    method_hits = ("credential", "exfil", "insider", "upload",
                   "dns", "usb")
    method_input = (findings.get("attack_method") or "").lower()
    method_ok = any(word in method_input for word in method_hits)

    report_summary = (findings.get("report_summary") or "").strip()

    checks = {
        "account": _match(findings.get("compromised_account", ""),
                          account),
        "timeline": _match(findings.get("timeline_start_time", ""),
                           timeline_start),
        "exfiltrated": _match(findings.get("exfiltrated_file", ""),
                              dl_filename),
        "ip": _match(findings.get("suspicious_ip", ""), suspicious_ip),
        "method": method_ok,
        "report": len(report_summary) >= 60,
    }
    checks["all_correct"] = all(checks.values())

    # Correlation is scored independently (informational — objectives
    # fire on ``correlation_complete`` when the student links every key
    # artifact into one graph).
    checks["correlation"] = correlation_score(case, links or [])
    return checks
