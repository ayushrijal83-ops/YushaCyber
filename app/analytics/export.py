"""Analytics export (YC-033.0) — CSV today, PDF-ready by design.

Every export is built from a `(title, headers, rows)` payload, so a
future PDF renderer consumes the exact same builders the CSV writer
does — no analytics logic will need to change to add PDF.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Iterable

from app.analytics import services

Payload = tuple[str, list[str], list[list[Any]]]


def overview_payload() -> Payload:
    stats = services.overview_stats()
    headers = ["Metric", "Value"]
    labels = {
        "total_students": "Total students",
        "active_students_7d": "Active students (7 days)",
        "completed_lessons": "Completed lessons",
        "completed_labs": "Completed labs",
        "completed_ctfs": "Completed CTF challenges",
        "certificates_issued": "Certificates issued",
        "avg_xp": "Average XP",
        "avg_level": "Average level",
    }
    rows = [[labels[key], stats[key]] for key in labels]
    return "YushaCyber — Analytics Overview", headers, rows


def students_payload(students: Iterable) -> Payload:
    headers = ["Username", "Email", "Level", "XP", "Streak", "Joined"]
    rows = [[user.username, user.email, user.level, user.xp,
             user.streak or 0,
             user.created_at.date().isoformat()
             if user.created_at else ""]
            for user in students]
    return "YushaCyber — Students", headers, rows


def labs_payload() -> Payload:
    data = services.lab_analytics()
    headers = ["Lab", "Difficulty", "Attempts", "Completed",
               "Failure rate %", "Avg completion (s)", "Hints used"]
    rows = [[r["lab"], r["difficulty"], r["attempts"], r["completed"],
             r["failure_rate"], r["avg_seconds"], r["hints_used"]]
            for r in data["rows"]]
    return "YushaCyber — Lab Analytics", headers, rows


def ctf_payload() -> Payload:
    data = services.ctf_analytics()
    headers = ["Challenge", "Difficulty", "Solves", "Avg attempts"]
    rows = [[r["challenge"], r["difficulty"], r["solves"],
             r["avg_attempts"]] for r in data["rows"]]
    return "YushaCyber — CTF Analytics", headers, rows


def roadmaps_payload() -> Payload:
    data = services.roadmap_analytics()
    headers = ["Roadmap", "Lessons", "Enrolled", "Completion rate %",
               "Avg lesson time (s)", "Biggest drop-off"]
    rows = []
    for r in data["rows"]:
        drop = (f"after “{r['drop_off']['after']}” "
                f"(-{r['drop_off']['lost']})") if r["drop_off"] else "—"
        rows.append([r["category"], r["lessons"], r["enrolled"],
                     r["completion_rate"], r["avg_lesson_seconds"], drop])
    return "YushaCyber — Roadmap Analytics", headers, rows


PAYLOADS = {
    "overview": overview_payload,
    "labs": labs_payload,
    "ctf": ctf_payload,
    "roadmaps": roadmaps_payload,
}


def to_csv(payload: Payload) -> str:
    """Render a payload as CSV text (UTF-8, Excel-friendly)."""
    title, headers, rows = payload
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([title])
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()
