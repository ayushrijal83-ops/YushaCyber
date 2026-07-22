"""Advanced Forensics lab seed (YC-029.5.4). Idempotent — safe to re-run.

Layers the third and final forensics case on top of applied:

  · case              — "Corporate Data Leak" (mode="advanced")
  · reuses all 6      — browser, downloads, event log, USB, login,
    fundamentals /      recent docs
    applied sources
  · new network       — DNS, HTTP, HTTPS, FTP, SMB, ICMP (all ride the
    sources             generic ForensicsArtifact table)
  · 3 suspects        — one marked ``is_key`` as the true actor
  · Lab               — forensics-advanced (+200 XP, Hard, 6 objectives)
  · Achievement       — Master Investigator (+100 bonus XP,
                        forensics_lab_completed >= 3)

Reuses every engine from the fundamentals + applied labs — nothing
duplicated. Notes and correlation links live in session state; they
never persist to the DB.
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.forensics.models import (
    ForensicsArtifact,
    ForensicsCase,
    ForensicsEvidence,
    ForensicsSuspect,
    ForensicsTimelineEvent,
)
from app.labs.models import Lab, LabCategory, LabObjective

CASE_LAB_SLUG = "forensics-advanced"
CASE_TITLE = "Case #YC-058 — Corporate Data Leak"
CASE_BRIEFING = (
    "A confidential product roadmap has surfaced on a competitor's "
    "blog. Three employees had access to the file; one workstation "
    "was seized after suspicious after-hours activity. You are the "
    "lead investigator. Correlate every source — including network "
    "traffic — to identify the compromised account, the exfil path, "
    "and the attack method."
)
CASE_WORKSTATION = "WORKSTATION-22"

# Minimal evidence rows for the Metadata panel (advanced lab is
# source- and network-driven, not evidence-driven).
ADVANCED_EVIDENCE = [
    ("roadmap-2026-pdf", "pdf", "roadmap-2026.pdf", "pdf",
     "system", 1_048_576, "2026-01-05 12:00", "2026-05-11 22:14",
     "Confidential product roadmap — accessed off-hours.",
     False, True, 1),
]
ADVANCED_TIMELINE = [
    ("21:47", "login", "Session started — vpn.remote", None),
    ("22:14", "file_modified", "roadmap-2026.pdf accessed",
     "roadmap-2026-pdf"),
    ("22:31", "logout", "Session ended", None),
]

# Suspects — three profiles, one is the actor.
# (slug, display_name, role, account, notes, is_key, order)
SUSPECTS = [
    ("srijan-kc", "Srijan KC", "Product Manager", "s.kc",
     "Weekend sysadmin credentials in shared vault; VPN access.",
     True, 1),
    ("anita-rai", "Anita Rai", "Software Engineer", "a.rai",
     "Was on approved leave during the incident window.",
     False, 2),
    ("bimal-lama", "Bimal Lama", "Marketing", "b.lama",
     "Read-only portal access; no VPN entitlement.",
     False, 3),
]

# Artifacts. Each source has one or more rows; the *_KEY marker
# is on the row a task expects the student to identify.
BROWSER_HISTORY = [
    ("21:52", {"url": "https://portal.acme.internal/",
               "title": "Company Portal",
               "visit_count": 42}, False),
    ("21:55", {"url": "https://drive.google.com/",
               "title": "Google Drive",
               "visit_count": 12}, False),
    ("22:20", {"url": "https://competitor-blog.example/leak",
               "title": "Competitor blog — draft roadmap",
               "visit_count": 1}, True),
]
DOWNLOADS = [
    ("22:24", {"filename": "roadmap-2026.pdf",
               "url": "https://drive.google.com/roadmap.pdf",
               "size_bytes": 1_048_576}, False),
    ("22:26", {"filename": "roadmap-2026-shared.zip",
               "url": "https://filedump.example/upload",
               "size_bytes": 1_265_408}, True),  # exfil archive
]
EVENT_LOG = [
    ("21:47", {"event_id": 4624, "event_type": "user_login",
               "description": "Successful VPN logon — s.kc",
               "user": "s.kc"}, True),
    ("22:14", {"event_id": 4663, "event_type": "file_modified",
               "description": "Object accessed — roadmap-2026.pdf",
               "user": "s.kc"}, False),
    ("22:26", {"event_id": 4688, "event_type": "process_started",
               "description": "curl.exe started",
               "user": "s.kc"}, False),
    ("22:31", {"event_id": 4634, "event_type": "user_logout",
               "description": "VPN session ended",
               "user": "s.kc"}, False),
]
USB_HISTORY = []  # advanced lab is network-based; no USB used
LOGIN_HISTORY = [
    ("21:47", {"username": "s.kc", "login_at": "21:47",
               "logout_at": "22:31", "duration": "00h 44m"}, True),
]
RECENT_DOCS = [
    ("22:14", {"filename": "roadmap-2026.pdf",
               "path": "C:\\Users\\s.kc\\Docs\\roadmap-2026.pdf",
               "last_accessed_at": "22:14"}, False),
]

# Network evidence.
NETWORK_DNS = [
    ("22:19", {"query": "filedump.example",
               "response_ip": "185.203.72.14",
               "domain": "filedump.example"}, True),
    ("22:20", {"query": "competitor-blog.example",
               "response_ip": "104.21.44.108",
               "domain": "competitor-blog.example"}, False),
]
NETWORK_HTTP = [
    ("22:24", {"method": "GET",
               "host": "drive.google.com",
               "path": "/roadmap.pdf",
               "response_code": 200,
               "bytes_sent": 1_048_576}, False),
]
NETWORK_HTTPS = [
    ("22:26", {"host": "filedump.example",
               "sni": "filedump.example",
               "bytes_sent": 1_265_408,
               "bytes_received": 512}, True),
]
NETWORK_FTP: list = []
NETWORK_SMB: list = []
NETWORK_ICMP = [
    ("22:19", {"host": "185.203.72.14",
               "message_type": "echo",
               "count": 4}, False),
]

SOURCES = {
    "browser_history": BROWSER_HISTORY,
    "downloads":       DOWNLOADS,
    "event_log":       EVENT_LOG,
    "usb_history":     USB_HISTORY,
    "login_history":   LOGIN_HISTORY,
    "recent_docs":     RECENT_DOCS,
    "network_dns":     NETWORK_DNS,
    "network_http":    NETWORK_HTTP,
    "network_https":   NETWORK_HTTPS,
    "network_ftp":     NETWORK_FTP,
    "network_smb":     NETWORK_SMB,
    "network_icmp":    NETWORK_ICMP,
}

# Six objectives (+200 XP total — 30 each on tasks 1–5, then 50 on task 6).
ADVANCED_OBJECTIVES = [
    ("Identify the compromised account",
     "Study the suspects panel and name the one whose behaviour matches "
     "the evidence.",
     "event_emitted",
     {"event": "key_suspect_named"},
     ["Three suspects had access.",
      "One was on leave; one has no VPN entitlement.",
      "Match the login-history username against each suspect's "
      "account handle."],
     30),
    ("Determine the attack timeline",
     "Enter the HH:MM the earliest key event started.",
     "state_flag",
     {"path": "checks.timeline", "equals": True},
     ["Multiple artifacts are marked as key.",
      "The earliest one anchors the incident's start.",
      "Look at the Login row: 21:47 kicks it off."],
     30),
    ("Identify the exfiltrated file",
     "Enter the filename of the archive uploaded off the corporate "
     "network.",
     "state_flag",
     {"path": "checks.exfiltrated", "equals": True},
     ["Downloads viewer lists two files.",
      "One went to a corporate host; one to filedump.example.",
      "Use the exact archive name shown."],
     30),
    ("Identify the suspicious IP",
     "Enter the response IP returned for the DNS lookup that started "
     "the exfil chain.",
     "state_flag",
     {"path": "checks.ip", "equals": True},
     ["The Network DNS viewer shows every lookup.",
      "One resolves to a host outside the company range.",
      "Copy its response_ip value verbatim."],
     30),
    ("Correlate the evidence",
     "Draw links between the key artifacts so they form one connected "
     "chain (VPN login → file access → curl → DNS → HTTPS upload).",
     "event_emitted",
     {"event": "correlation_complete"},
     ["Click two key artifacts and hit Link.",
      "Every red-highlighted row must be joined to the chain.",
      "The Evidence Correlation panel shows your progress."],
     30),
    ("Submit the incident report",
     "Describe the attack method and provide a report summary of "
     "at least 60 characters. All findings must be correct.",
     "event_emitted",
     {"event": "findings_correct"},
     ["Attack method should mention how the archive left the network.",
      "'Insider credential misuse + HTTPS exfil' is a good phrasing.",
      "The Recommendations text field just needs 60+ characters."],
     50),
]


def _upsert_advanced_case() -> ForensicsCase:
    case = ForensicsCase.query.filter_by(lab_slug=CASE_LAB_SLUG).first()
    if case is None:
        case = ForensicsCase(lab_slug=CASE_LAB_SLUG)
        db.session.add(case)
    case.title = CASE_TITLE
    case.briefing = CASE_BRIEFING
    case.workstation_name = CASE_WORKSTATION
    case.investigator = "Investigator Ayush"
    case.mode = "advanced"
    db.session.flush()

    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    ForensicsSuspect.query.filter_by(case_id=case.id).delete()
    db.session.flush()

    for (slug, kind, filename, ext, owner, size, created, modified,
         notes, suspicious, modified_flag, order) in ADVANCED_EVIDENCE:
        db.session.add(ForensicsEvidence(
            case_id=case.id, slug=slug, kind=kind, filename=filename,
            extension=ext, owner=owner, size_bytes=size,
            created_at_display=created, modified_at_display=modified,
            notes=notes, is_suspicious=suspicious,
            is_modified=modified_flag, display_order=order))
    for at_time, kind, description, evidence_slug in ADVANCED_TIMELINE:
        db.session.add(ForensicsTimelineEvent(
            case_id=case.id, at_time=at_time, kind=kind,
            description=description, evidence_slug=evidence_slug))
    for slug, name, role, account, notes, is_key, order in SUSPECTS:
        db.session.add(ForensicsSuspect(
            case_id=case.id, slug=slug, display_name=name,
            role=role, account=account, notes=notes,
            is_key=is_key, display_order=order))

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


def _upsert_advanced_lab(category: LabCategory,
                         prerequisite_slug: str | None) -> Lab:
    lab = Lab.query.filter_by(slug=CASE_LAB_SLUG).first()
    if lab is None:
        lab = Lab(slug=CASE_LAB_SLUG)
        db.session.add(lab)
    lab.category_id = category.id
    lab.title = "Digital Forensics: Advanced"
    lab.description = (
        "Lead the investigation of a simulated corporate data leak. "
        "Correlate browser, downloads, event log, login, USB, recent "
        "documents AND network evidence (DNS, HTTP, HTTPS, ICMP) to "
        "identify the actor, the exfil path and the attack method.")
    lab.difficulty = "Hard"
    lab.estimated_minutes = 50
    lab.xp_reward = 200
    lab.display_order = 3
    lab.is_active = True
    lab.simulator_key = "forensics"
    lab.is_interactive = True
    prerequisite = None
    if prerequisite_slug:
        prerequisite = Lab.query.filter_by(slug=prerequisite_slug).first()
    lab.prerequisite_lab_id = prerequisite.id if prerequisite else None
    db.session.flush()

    for order, (title, instruction, vtype, vdata, hints, xp) in \
            enumerate(ADVANCED_OBJECTIVES, start=1):
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


def _upsert_master_achievement() -> None:
    """Master Investigator — +100 bonus XP on the third forensics lab
    completion. Reuses the ``forensics_lab_completed`` metric."""
    achievement = Achievement.query.filter_by(
        title="Master Investigator").first()
    if achievement is None:
        achievement = Achievement(title="Master Investigator")
        db.session.add(achievement)
    achievement.description = ("Completed every Digital Forensics lab "
                               "including the advanced investigation.")
    achievement.icon = "🎖"
    achievement.category = "digital-forensics"
    achievement.condition_type = "forensics_lab_completed"
    achievement.condition_value = 3
    achievement.bonus_xp = 100
    achievement.is_active = True
    achievement.display_order = 92


def seed_forensics_advanced_lab() -> dict[str, int]:
    """Seed the advanced case + lab + achievement. Idempotent."""
    result = {"case": 0, "labs": 0, "objectives": 0,
              "achievements": 0, "artifacts": 0, "suspects": 0}

    category = LabCategory.query.filter_by(
        slug="digital-forensics").first()
    if category is None:
        category = LabCategory(slug="digital-forensics",
                               name="Digital Forensics",
                               display_order=80, is_active=True)
        db.session.add(category)
        db.session.flush()

    _upsert_advanced_case()
    result["case"] = 1
    result["artifacts"] = sum(len(rows) for rows in SOURCES.values())
    result["suspects"] = len(SUSPECTS)

    _upsert_advanced_lab(category, prerequisite_slug="forensics-applied")
    result["labs"] = 1
    result["objectives"] = len(ADVANCED_OBJECTIVES)

    _upsert_master_achievement()
    result["achievements"] = 1
    db.session.commit()
    return result
