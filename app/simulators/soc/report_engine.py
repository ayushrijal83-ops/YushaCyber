"""SOC report engine.

Wraps the forensics findings validator with SOC-specific checks:
was the right playbook picked, does the root-cause text look right,
was every checklist item ticked, and does the report body meet the
length + section-mention requirements.
"""

from __future__ import annotations

from typing import Any

from app.simulators.soc.models import SocAlert, SocChecklistItem

#: The SOC report is expected to touch each of these terms (case
#: insensitive). Not a hard match — a summary is prose, not a form.
REPORT_SECTIONS = (
    "summary", "timeline", "evidence", "root cause",
    "actions", "recommendation",
)


def evaluate_report(alert: SocAlert,
                    checklist_items: list[SocChecklistItem],
                    submission: dict[str, Any]) -> dict[str, Any]:
    """Grade a SOC closure submission.

    submission keys:
      playbook_alert_type  — the alert_type slug the student chose
      root_cause           — free text root-cause statement
      report               — free text final report
      checked              — list of checklist slugs the student ticked
    """
    def _contains(text: str, needle: str) -> bool:
        return needle.lower() in (text or "").lower()

    playbook_ok = ((submission.get("playbook_alert_type") or "")
                   == alert.alert_type)
    root_cause = (submission.get("root_cause") or "").strip()
    root_cause_ok = _root_cause_matches(alert.alert_type, root_cause)

    report = (submission.get("report") or "").strip()
    report_len_ok = len(report) >= 120
    sections_ok = sum(1 for s in REPORT_SECTIONS
                      if _contains(report, s)) >= 3

    checked = set(submission.get("checked") or [])
    required_slugs = {c.slug for c in checklist_items if c.is_required}
    checklist_ok = required_slugs.issubset(checked)

    checks = {
        "playbook":  playbook_ok,
        "root_cause": bool(root_cause) and root_cause_ok,
        "report_length": report_len_ok,
        "report_sections": sections_ok,
        "checklist":  checklist_ok,
    }
    checks["all_correct"] = all(checks.values())
    return checks


# Keyword hits per alert type — deliberately forgiving so students can
# phrase root causes naturally.
_ROOT_CAUSE_HITS = {
    "data_exfiltration":   ("exfil", "leak", "upload", "insider",
                            "credential"),
    "possible_malware":    ("malware", "trojan", "backdoor", "loader"),
    "suspicious_powershell": ("powershell", "encoded", "downloader",
                              "living-off"),
    "multiple_failed_logins": ("brute", "password", "credential", "spray"),
    "dns_tunneling":       ("dns", "tunnel", "c2", "beacon"),
    "suspicious_http_traffic": ("http", "beacon", "c2", "cnc"),
    "usb_activity":        ("usb", "removable", "physical", "insider"),
    "privilege_escalation": ("privilege", "escalation", "admin", "root"),
}


def _root_cause_matches(alert_type: str, root_cause: str) -> bool:
    hits = _ROOT_CAUSE_HITS.get(alert_type, ())
    text = root_cause.lower()
    return any(h in text for h in hits)
