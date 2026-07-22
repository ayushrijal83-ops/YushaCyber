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
    }
