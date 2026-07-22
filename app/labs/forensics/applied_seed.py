"""Applied Forensics lab seed (YC-029.5.3). Idempotent — safe to re-run.

Layers a second case, lab and achievement on top of the fundamentals
seed:

  · case             — "Insider Exfil" (mode="applied")
  · sources          — browser history, downloads, event log,
                       USB history, login history, recent documents
  · Lab              — forensics-applied (+100 XP, Medium, 6 objectives)
  · Achievement      — Evidence Correlator (+50 bonus XP,
                       forensics_lab_completed >= 2 — reusing the
                       metric added in YC-029.5.2)
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.forensics.models import (
    ForensicsArtifact,
    ForensicsCase,
    ForensicsEvidence,
    ForensicsTimelineEvent,
)
from app.labs.models import Lab, LabCategory, LabObjective

# ---------------------------------------------------------------------------
# The applied case.
# ---------------------------------------------------------------------------
CASE_LAB_SLUG = "forensics-applied"
CASE_TITLE = "Case #YC-041 — Insider Exfil"
CASE_BRIEFING = (
    "A company suspects an employee copied confidential information "
    "before submitting their resignation. Investigate the workstation, "
    "correlate every evidence source, and reconstruct exactly what "
    "happened."
)
CASE_WORKSTATION = "WORKSTATION-14"

# Base "evidence" rows still power the Metadata / Hash panels.
# (slug, kind, filename, ext, owner, size_bytes, created, modified,
#  notes, is_suspicious, is_modified, display_order)
APPLIED_EVIDENCE = [
    ("client-list-xlsx", "document", "client-list.xlsx", "xlsx",
     "d.moktan", 328_704,
     "2025-11-14 10:30", "2026-04-30 15:52",
     "Master client database — modified on the resignation day.",
     False, True, 1),
    ("nda-pdf", "pdf", "nda.pdf", "pdf",
     "d.moktan", 156_672,
     "2024-06-01 09:00", "2024-06-01 09:00",
     "Signed NDA — untouched.", False, False, 2),
]

# (at_time, kind, description, evidence_slug)
APPLIED_TIMELINE = [
    ("08:07", "login", "Session started — d.moktan", None),
    ("15:41", "usb", "USB device connected: KINGSTON DT (E:)", None),
    ("15:52", "file_modified", "client-list.xlsx modified",
     "client-list-xlsx"),
    ("16:12", "download", "Browser download: portfolio.zip", None),
    ("16:33", "recycle_bin", "browser cache cleared", None),
    ("16:40", "logout", "Session ended — d.moktan", None),
]

# ---------------------------------------------------------------------------
# Artifact sources — one row per artifact. is_key marks the single row
# each applied-lab task expects the student to identify.
# ---------------------------------------------------------------------------
# Browser history — the pastebin drop is the suspicious one.
BROWSER_HISTORY = [
    ("08:15", {"url": "https://portal.acme.internal/",
               "title": "Company Portal",
               "visit_count": 5}, False),
    ("08:22", {"url": "https://github.com/dmoktan",
               "title": "GitHub — dmoktan",
               "visit_count": 12}, False),
    ("09:03", {"url": "https://drive.google.com/",
               "title": "Google Drive",
               "visit_count": 3}, False),
    ("11:47", {"url": "https://docs.acme.internal/api",
               "title": "Internal API docs",
               "visit_count": 2}, False),
    ("15:38", {"url": "https://pastebin.com/raw/9Zx4KpQ2",
               "title": "Untitled paste — pastebin.com",
               "visit_count": 1}, True),   # KEY: suspicious drop
    ("16:10", {"url": "https://filedump.example/upload",
               "title": "Anonymous file drop",
               "visit_count": 1}, False),
]

# Downloads — portfolio.zip is the key exfil artefact.
DOWNLOADS = [
    ("11:52", {"filename": "sdk-docs.zip",
               "url": "https://docs.acme.internal/sdk-docs.zip",
               "size_bytes": 2_048_000}, False),
    ("16:12", {"filename": "portfolio.zip",
               "url": "https://filedump.example/portfolio.zip",
               "size_bytes": 9_437_184}, True),   # KEY
]

# Event log — the login sets the earliest key event.
EVENT_LOG = [
    ("08:07", {"event_id": 4624, "event_type": "user_login",
               "description": "Successful logon — d.moktan (interactive)",
               "user": "d.moktan"}, False),
    ("08:15", {"event_id": 5379, "event_type": "browser_started",
               "description": "Firefox process started",
               "user": "d.moktan"}, False),
    ("15:41", {"event_id": 20003, "event_type": "usb_connected",
               "description": "USB device connected: KINGSTON DT (E:)",
               "user": "system"}, False),
    ("15:52", {"event_id": 4663, "event_type": "file_modified",
               "description": "Object modified — client-list.xlsx",
               "user": "d.moktan"}, False),
    ("16:12", {"event_id": 4688, "event_type": "file_opened",
               "description": "Object opened — portfolio.zip",
               "user": "d.moktan"}, False),
    ("16:33", {"event_id": 20004, "event_type": "usb_removed",
               "description": "USB device removed: KINGSTON DT (E:)",
               "user": "system"}, False),
    ("16:40", {"event_id": 4634, "event_type": "user_logout",
               "description": "Session ended — d.moktan",
               "user": "d.moktan"}, False),
]

# USB history — Kingston is the rogue device.
USB_HISTORY = [
    ("09:12", {"device_name": "TOSHIBA-USB (F:)",
               "serial_number": "TSH-8811-A3",
               "connected_at": "09:12", "removed_at": "09:47"}, False),
    ("15:41", {"device_name": "KINGSTON DT (E:)",
               "serial_number": "KDT-7YQ-4419",
               "connected_at": "15:41", "removed_at": "16:33"},
     True),   # KEY
]

# Login history — the interactive session is the key one.
LOGIN_HISTORY = [
    ("08:07", {"username": "d.moktan",
               "login_at": "08:07", "logout_at": "16:40",
               "duration": "08h 33m"}, True),   # KEY
    ("22:14", {"username": "svc.backup",
               "login_at": "22:14", "logout_at": "22:16",
               "duration": "00h 02m"}, False),
]

# Recent documents — spread of files the user touched.
RECENT_DOCS = [
    ("15:52", {"filename": "client-list.xlsx",
               "path": "C:\\Users\\d.moktan\\Documents\\client-list.xlsx",
               "last_accessed_at": "15:52"}, False),
    ("14:33", {"filename": "notes.txt",
               "path": "C:\\Users\\d.moktan\\Documents\\notes.txt",
               "last_accessed_at": "14:33"}, False),
    ("11:47", {"filename": "api-spec.md",
               "path": "C:\\Users\\d.moktan\\Documents\\api-spec.md",
               "last_accessed_at": "11:47"}, False),
]

SOURCES = {
    "browser_history": BROWSER_HISTORY,
    "downloads":       DOWNLOADS,
    "event_log":       EVENT_LOG,
    "usb_history":     USB_HISTORY,
    "login_history":   LOGIN_HISTORY,
    "recent_docs":     RECENT_DOCS,
}

# ---------------------------------------------------------------------------
# Six applied-lab objectives (+100 XP total = 15/15/15/15/20/20).
# Each rides an existing validator; no new validator types needed.
# ---------------------------------------------------------------------------
# (title, instruction, validator_type, validator_data, hints, xp)
APPLIED_OBJECTIVES = [
    ("Open every evidence source",
     "Click each of the six source tabs to load its viewer.",
     "event_emitted",
     {"event": "all_sources_opened"},
     ["The tabs are Browser History, Downloads, Windows Event Log, "
      "USB Devices, Login Sessions, Recent Documents.",
      "Every tab must be opened at least once before you submit.",
      "Watch the status panel — it tracks how many sources you've "
      "loaded."],
     15),
    ("Determine the first login",
     "Enter the time of the interactive login session in your report.",
     "state_flag",
     {"path": "checks.first_login", "equals": True},
     ["Login sessions live in the Login Sessions viewer.",
      "There's a night-time service session and a daytime interactive "
      "one — you want the interactive one.",
      "Copy the login_at field for the interactive session."],
     15),
    ("Identify the rogue USB device",
     "Enter the serial number of the USB that wasn't already approved.",
     "state_flag",
     {"path": "checks.usb_serial", "equals": True},
     ["Two USB devices connected during the day.",
      "One session correlates with the client-list modification.",
      "Copy the KINGSTON DT serial number verbatim."],
     15),
    ("Identify the exfil download",
     "Enter the filename of the download that left the corporate network.",
     "state_flag",
     {"path": "checks.download", "equals": True},
     ["The Downloads viewer lists everything the browser saved.",
      "One archive was fetched from a non-corporate host.",
      "Use the exact filename shown in the viewer."],
     15),
    ("Reconstruct the full timeline",
     "State what kind of event kicked off the day (source label).",
     "state_flag",
     {"path": "checks.timeline", "equals": True},
     ["The unified timeline merges every source chronologically.",
      "Scroll to the top — the earliest row is the day's first event.",
      "Enter the source label of that row (event_log, login_history, "
      "usb_history, browser_history, downloads, recent_docs)."],
     20),
    ("Submit the investigation report",
     "Complete the Suspicious website field and write a 40+ character "
     "summary. When every check passes the case closes.",
     "event_emitted",
     {"event": "findings_correct"},
     ["The Suspicious Findings row is the pastebin drop.",
      "The report summary needs at least 40 characters — a short "
      "paragraph is plenty.",
      "All six fields must be correct simultaneously."],
     20),
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------
def _upsert_applied_case() -> ForensicsCase:
    case = ForensicsCase.query.filter_by(lab_slug=CASE_LAB_SLUG).first()
    if case is None:
        case = ForensicsCase(lab_slug=CASE_LAB_SLUG)
        db.session.add(case)
    case.title = CASE_TITLE
    case.briefing = CASE_BRIEFING
    case.workstation_name = CASE_WORKSTATION
    case.investigator = "Investigator Ayush"
    case.mode = "applied"
    db.session.flush()

    # Rebuild every child collection deterministically.
    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for (slug, kind, filename, ext, owner, size, created, modified,
         notes, suspicious, modified_flag, order) in APPLIED_EVIDENCE:
        db.session.add(ForensicsEvidence(
            case_id=case.id, slug=slug, kind=kind, filename=filename,
            extension=ext, owner=owner, size_bytes=size,
            created_at_display=created, modified_at_display=modified,
            notes=notes, is_suspicious=suspicious,
            is_modified=modified_flag, display_order=order))
    for at_time, kind, description, evidence_slug in APPLIED_TIMELINE:
        db.session.add(ForensicsTimelineEvent(
            case_id=case.id, at_time=at_time, kind=kind,
            description=description, evidence_slug=evidence_slug))

    order = 0
    for source_type, rows in SOURCES.items():
        for at_time, data, is_key in rows:
            order += 1
            artifact = ForensicsArtifact(
                case_id=case.id, source_type=source_type,
                at_time=at_time, is_key=is_key, sort_order=order)
            artifact.set_data(data)
            db.session.add(artifact)
    return case


def _upsert_applied_lab(category: LabCategory,
                        prerequisite_slug: str | None) -> Lab:
    lab = Lab.query.filter_by(slug=CASE_LAB_SLUG).first()
    if lab is None:
        lab = Lab(slug=CASE_LAB_SLUG)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = "Digital Forensics: Applied"
    lab.description = (
        "Correlate browser history, downloads, event logs, USB devices "
        "and login sessions to reconstruct an insider exfil incident.")
    lab.difficulty = "Medium"
    lab.estimated_minutes = 35
    lab.xp_reward = 100
    lab.display_order = 2
    lab.is_active = True
    lab.simulator_key = "forensics"
    lab.is_interactive = True
    prerequisite = None
    if prerequisite_slug:
        prerequisite = Lab.query.filter_by(slug=prerequisite_slug).first()
    lab.prerequisite_lab_id = prerequisite.id if prerequisite else None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(APPLIED_OBJECTIVES, start=1):
        objective = LabObjective.query.filter_by(
            lab_id=lab.id, title=title).first()
        if objective is None:
            objective = LabObjective(lab_id=lab.id, title=title)
            db.session.add(objective)
        objective.description = instruction
        objective.instruction = instruction
        objective.display_order = order
        objective.validator_type = vtype
        objective.set_validator_data(vdata)
        objective.hint1 = hints[0] if len(hints) > 0 else None
        objective.hint2 = hints[1] if len(hints) > 1 else None
        objective.hint3 = hints[2] if len(hints) > 2 else None
        objective.xp_reward = xp
        objective.is_optional = False
    return lab


def _upsert_correlator_achievement() -> None:
    """Evidence Correlator — +50 bonus XP on the second forensics lab
    completion. Reuses the ``forensics_lab_completed`` metric added in
    YC-029.5.2."""
    achievement = Achievement.query.filter_by(
        title="Evidence Correlator").first()
    if achievement is None:
        achievement = Achievement(title="Evidence Correlator")
        db.session.add(achievement)
    achievement.description = ("Correlated multiple evidence sources "
                               "to reconstruct an incident.")
    achievement.icon = "🧩"
    achievement.category = "digital-forensics"
    achievement.condition_type = "forensics_lab_completed"
    achievement.condition_value = 2
    achievement.bonus_xp = 50
    achievement.is_active = True
    achievement.display_order = 91


def seed_forensics_applied_lab() -> dict[str, int]:
    """Seed the applied case + lab + achievement. Idempotent."""
    result = {"case": 0, "labs": 0, "objectives": 0,
              "achievements": 0, "artifacts": 0}

    category = LabCategory.query.filter_by(
        slug="digital-forensics").first()
    if category is None:
        # The fundamentals seed creates the category; if we're seeding
        # applied first (unusual), fall back to creating it here.
        category = LabCategory(slug="digital-forensics",
                               name="Digital Forensics",
                               display_order=80, is_active=True)
        db.session.add(category)
        db.session.flush()

    _upsert_applied_case()
    result["case"] = 1
    result["artifacts"] = sum(len(rows) for rows in SOURCES.values())

    _upsert_applied_lab(category, prerequisite_slug="forensics-fundamentals")
    result["labs"] = 1
    result["objectives"] = len(APPLIED_OBJECTIVES)

    _upsert_correlator_achievement()
    result["achievements"] = 1
    db.session.commit()
    return result
