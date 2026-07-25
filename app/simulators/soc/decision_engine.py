"""Decision engine for SOC Incident Response (YC-030.3).

Students choose actions at each IR phase. Each decision is graded
against the incident's expected-action set. Wrong choices reduce
the running score; correct ones increase it.

Reusable: future IR scenarios just seed a different decision set.
"""

from __future__ import annotations

from typing import Any

#: Every possible action the student can take. Seeded incidents
#: specify which ones are correct per phase.
AVAILABLE_ACTIONS = (
    "disconnect_host", "reset_password", "block_ip",
    "quarantine_file", "ignore_alert", "restore_backup",
    "isolate_network_segment", "revoke_credentials",
    "scan_endpoints", "preserve_evidence", "notify_management",
    "update_firewall_rules", "patch_vulnerability",
    "rotate_api_keys", "enable_mfa",
)

ACTION_LABELS = {
    "disconnect_host": "Disconnect Host",
    "reset_password": "Reset Password",
    "block_ip": "Block IP",
    "quarantine_file": "Quarantine File",
    "ignore_alert": "Ignore Alert",
    "restore_backup": "Restore Backup",
    "isolate_network_segment": "Isolate Network Segment",
    "revoke_credentials": "Revoke Credentials",
    "scan_endpoints": "Scan Endpoints",
    "preserve_evidence": "Preserve Evidence",
    "notify_management": "Notify Management",
    "update_firewall_rules": "Update Firewall Rules",
    "patch_vulnerability": "Patch Vulnerability",
    "rotate_api_keys": "Rotate API Keys",
    "enable_mfa": "Enable MFA",
}

#: Points per correct / wrong decision.
CORRECT_POINTS = 10
WRONG_PENALTY = -5


def grade_decision(action: str,
                   correct_actions: list[str],
                   wrong_actions: list[str] | None = None) -> dict[str, Any]:
    """Grade a single student decision.

    Returns ``{"action", "correct", "points", "feedback"}``.
    """
    action = action.strip().lower()
    if action in correct_actions:
        return {
            "action": action, "correct": True,
            "points": CORRECT_POINTS,
            "feedback": f"✓ {ACTION_LABELS.get(action, action)} — correct.",
        }
    label = ACTION_LABELS.get(action, action)
    if wrong_actions and action in wrong_actions:
        return {
            "action": action, "correct": False,
            "points": WRONG_PENALTY,
            "feedback": f"✖ {label} — wrong choice for this phase.",
        }
    # Neutral — not in either list (harmless but unhelpful).
    return {
        "action": action, "correct": False,
        "points": 0,
        "feedback": f"— {label} — not applicable here.",
    }


def score_decisions(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate all decisions into a score + rating."""
    total = sum(d.get("points", 0) for d in decisions)
    correct = sum(1 for d in decisions if d.get("correct"))
    wrong = sum(1 for d in decisions if not d.get("correct")
                and d.get("points", 0) < 0)
    max_possible = max(1, len(decisions)) * CORRECT_POINTS
    ratio = total / max_possible if max_possible > 0 else 0.0
    if ratio >= 0.8:
        rating = "Excellent"
    elif ratio >= 0.5:
        rating = "Good"
    else:
        rating = "Needs Improvement"
    return {
        "total_points": total,
        "correct": correct,
        "wrong": wrong,
        "decisions": len(decisions),
        "ratio": round(ratio, 2),
        "rating": rating,
    }
