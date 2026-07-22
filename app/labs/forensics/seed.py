"""Forensics lab seed (YC-029.5.2). Idempotent — safe to re-run.

Creates:
  · the built-in "Missing Files" case for the "forensics-fundamentals" lab
  · the LabCategory "Digital Forensics" (if absent) and SimulatorEngine row
  · the Lab + LabObjectives (5 tasks) driving the workflow
  · the "First Investigator" achievement with +25 bonus XP
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.forensics.models import (
    ForensicsCase,
    ForensicsEvidence,
    ForensicsTimelineEvent,
)
from app.labs.models import Lab, LabCategory, LabObjective, SimulatorEngine

# The built-in case.
CASE_LAB_SLUG = "forensics-fundamentals"
CASE_TITLE = "Case #YC-034 — Missing Files"
CASE_BRIEFING = (
    "An employee reported that several company files disappeared "
    "after they returned from lunch. Your job is to investigate the "
    "workstation, identify which file was modified, when, and whether "
    "any suspicious activity took place."
)
CASE_WORKSTATION = "WORKSTATION-07"
CASE_INVESTIGATOR = "Investigator Ayush"

# (slug, kind, filename, ext, owner, size_bytes, created, modified,
#  notes, is_suspicious, is_modified, display_order)
EVIDENCE = [
    ("report-docx", "document", "report.docx", "docx", "j.smith",
     45_120, "2026-04-17 08:22", "2026-04-17 08:22",
     "Quarterly report — untouched after creation.",
     False, False, 1),
    ("confidential-pdf", "pdf", "confidential.pdf", "pdf", "j.smith",
     182_400, "2026-03-01 09:15", "2026-04-17 08:35",
     "Legal file. Modified on the day of the incident — investigate.",
     False, True, 2),
    ("holiday-jpg", "image", "holiday.jpg", "jpg", "j.smith",
     2_048_000, "2025-12-20 14:03", "2025-12-20 14:03",
     "Personal photo — unrelated to the incident.",
     False, False, 3),
    ("backup-zip", "archive", "backup.zip", "zip", "j.smith",
     8_388_608, "2026-04-10 17:45", "2026-04-10 17:45",
     "Prior week's backup archive.", False, False, 4),
    ("usb-toshiba", "usb", "TOSHIBA-USB (E:)", "", "system",
     0, "2026-04-17 08:18", "2026-04-17 08:18",
     "Unknown USB device connected minutes before the modification. "
     "Not on the approved-device list.",
     True, False, 5),
    ("browser-history", "browser", "browser-history.sqlite", "sqlite",
     "j.smith", 65_536, "2026-04-17 07:59", "2026-04-17 08:41",
     "Browser history recorded a download at 08:41.",
     False, False, 6),
    ("resume-pdf", "download", "resume_final.pdf", "pdf", "j.smith",
     512_000, "2026-04-17 08:41", "2026-04-17 08:41",
     "Downloaded via the browser at 08:41 — origin: personal cloud drive.",
     False, False, 7),
    ("recycle-old-notes", "recycle_bin", "old_notes.txt", "txt",
     "j.smith", 4_096, "2026-04-03 10:12", "2026-04-17 08:55",
     "Placed in the recycle bin during the session — recoverable.",
     False, False, 8),
]

# (at_time, kind, description, evidence_slug)
TIMELINE = [
    ("08:12", "login", "Login — j.smith (interactive session)", None),
    ("08:18", "usb", "USB device connected: TOSHIBA-USB (E:)",
     "usb-toshiba"),
    ("08:22", "file_created", "report.docx created", "report-docx"),
    ("08:35", "file_modified", "confidential.pdf modified",
     "confidential-pdf"),
    ("08:41", "download", "Browser download: resume_final.pdf",
     "resume-pdf"),
    ("08:55", "recycle_bin", "old_notes.txt sent to Recycle Bin",
     "recycle-old-notes"),
    ("09:03", "logout", "Logout — session ended", None),
]

# The five tasks driving XP + achievements. Uses existing validators.
# (title, instruction, validator_type, validator_data, hints, xp)
OBJECTIVES = [
    ("Locate the modified file",
     "Open every evidence item and find the one whose Modified time "
     "differs from its Created time.",
     "event_emitted",
     {"event": "all_evidence_inspected"},
     ["Click each item in the Evidence Explorer to inspect it.",
      "Watch the metadata panel — a mismatch between Created and "
      "Modified means the file was touched later.",
      "confidential.pdf shows Created in March but Modified on the "
      "incident day."],
     10),
    ("Identify its SHA-256 hash",
     "Copy the SHA-256 of the modified file into the Findings form.",
     "state_flag",
     {"path": "checks.modified_hash", "equals": True},
     ["The metadata panel shows both MD5 and SHA-256.",
      "SHA-256 is 64 hex characters long — MD5 is 32.",
      "Paste the value into 'SHA-256 of modified file' in the Findings."],
     10),
    ("Determine when the file changed",
     "Find the timeline entry for the modification and enter its HH:MM.",
     "state_flag",
     {"path": "checks.modified_time", "equals": True},
     ["The timeline lists every recorded event.",
      "Look for 'file_modified' rows — one of them points at the file.",
      "Enter the time exactly as shown, e.g. '08:35'."],
     10),
    ("Identify the suspicious evidence",
     "Flag the item that does not belong on this workstation and "
     "select it in the Findings form.",
     "event_emitted",
     {"event": "suspicious_flagged"},
     ["Something arrived just before the file was modified.",
      "USB devices should be on the approved list; this one isn't.",
      "Click Flag on the TOSHIBA-USB entry."],
     10),
    ("Submit correct findings",
     "Complete the Findings form and submit for review.",
     "state_flag",
     {"path": "findings_correct", "equals": True},
     ["All four fields must match the ground truth.",
      "Modified file, its SHA-256, its time, and the suspicious item.",
      "Everything you need is in the metadata panel and timeline."],
     10),
]


def _upsert_case() -> ForensicsCase:
    case = ForensicsCase.query.filter_by(lab_slug=CASE_LAB_SLUG).first()
    if case is None:
        case = ForensicsCase(lab_slug=CASE_LAB_SLUG)
        db.session.add(case)
    case.title = CASE_TITLE
    case.briefing = CASE_BRIEFING
    case.workstation_name = CASE_WORKSTATION
    case.investigator = CASE_INVESTIGATOR
    db.session.flush()

    # Wipe & re-insert evidence + timeline so admin edits stay
    # deterministic across re-seeds — the case row survives.
    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for (slug, kind, filename, ext, owner, size, created, modified,
         notes, suspicious, modified_flag, order) in EVIDENCE:
        db.session.add(ForensicsEvidence(
            case_id=case.id, slug=slug, kind=kind, filename=filename,
            extension=ext, owner=owner, size_bytes=size,
            created_at_display=created, modified_at_display=modified,
            notes=notes, is_suspicious=suspicious,
            is_modified=modified_flag, display_order=order))
    for at_time, kind, description, evidence_slug in TIMELINE:
        db.session.add(ForensicsTimelineEvent(
            case_id=case.id, at_time=at_time, kind=kind,
            description=description, evidence_slug=evidence_slug))
    return case


def _upsert_lab_and_objectives(category: LabCategory) -> Lab:
    lab = Lab.query.filter_by(slug=CASE_LAB_SLUG).first()
    if lab is None:
        lab = Lab(slug=CASE_LAB_SLUG)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = "Digital Forensics: Fundamentals"
    lab.description = (
        "Investigate a workstation where an employee accidentally "
        "deleted files. Inspect evidence, read metadata, follow the "
        "timeline and report your findings.")
    lab.difficulty = "Easy"
    lab.estimated_minutes = 25
    lab.xp_reward = 50
    lab.display_order = 1
    lab.is_active = True
    lab.simulator_key = "forensics"
    lab.is_interactive = True
    lab.prerequisite_lab_id = None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(OBJECTIVES, start=1):
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


def _upsert_achievement() -> None:
    """First Investigator — +25 bonus XP on the first forensics lab
    completion. Uses the existing achievement engine's condition
    metric (``forensics_labs_completed``, added alongside this seed)."""
    achievement = Achievement.query.filter_by(
        title="First Investigator").first()
    if achievement is None:
        achievement = Achievement(title="First Investigator")
        db.session.add(achievement)
    achievement.description = ("Completed your first Digital Forensics "
                               "lab.")
    achievement.icon = "🕵"
    achievement.category = "digital-forensics"
    achievement.condition_type = "forensics_lab_completed"
    achievement.condition_value = 1
    achievement.bonus_xp = 25
    achievement.is_active = True
    achievement.display_order = 90


def seed_forensics_labs() -> dict[str, int]:
    """Seed the Forensics category, engine row, case, lab + objectives
    and the First Investigator achievement. Idempotent by slug/title.

    Also seeds the Applied lab (YC-029.5.3) so the whole Digital
    Forensics track ships in one call.
    """
    result = {"case": 0, "labs": 0, "objectives": 0, "achievements": 0}

    category = LabCategory.query.filter_by(
        slug="digital-forensics").first()
    if category is None:
        category = LabCategory(slug="digital-forensics")
        db.session.add(category)
    category.name = "Digital Forensics"
    category.description = ("Investigate simulated workstations — "
                            "evidence, metadata, hashes and timelines.")
    category.icon = "search"
    category.display_order = 80
    category.is_active = True
    db.session.flush()

    engine_row = SimulatorEngine.query.filter_by(key="forensics").first()
    if engine_row is None:
        engine_row = SimulatorEngine(key="forensics")
        db.session.add(engine_row)
    engine_row.name = "Digital Forensics Simulator"
    engine_row.description = ("Simulated forensic workstation: evidence "
                              "explorer, metadata, hash viewer, timeline "
                              "and findings report.")
    engine_row.capabilities = "inspector"
    engine_row.is_active = True
    db.session.flush()

    _upsert_case()
    result["case"] = 1
    _upsert_lab_and_objectives(category)
    result["labs"] = 1
    result["objectives"] = len(OBJECTIVES)
    _upsert_achievement()
    result["achievements"] = 1

    # YC-029.5.3 — layer the applied lab on top.
    from app.labs.forensics.applied_seed import seed_forensics_applied_lab
    applied = seed_forensics_applied_lab()
    result["labs"] += applied.get("labs", 0)
    result["objectives"] += applied.get("objectives", 0)
    result["achievements"] += applied.get("achievements", 0)
    result["applied_artifacts"] = applied.get("artifacts", 0)

    # YC-029.5.4 — layer the advanced lab on top of applied.
    from app.labs.forensics.advanced_seed import seed_forensics_advanced_lab
    advanced = seed_forensics_advanced_lab()
    result["labs"] += advanced.get("labs", 0)
    result["objectives"] += advanced.get("objectives", 0)
    result["achievements"] += advanced.get("achievements", 0)
    result["advanced_artifacts"] = advanced.get("artifacts", 0)
    result["advanced_suspects"] = advanced.get("suspects", 0)

    db.session.commit()
    return result
