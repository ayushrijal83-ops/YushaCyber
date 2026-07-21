"""Policy Engine (YC-032.0) — account password policy + the risk library.

The risk library backs the labs' "explain the risk" step: `risk <topic>`
prints impact, real-world context and the fix, and emits the
`risk_reviewed` event the objectives validate.
"""

from __future__ import annotations

from typing import Any

from app.labs.cloud.engine import OpResult

BASELINE_MIN_LENGTH = 12

RISKS: dict[str, dict[str, str]] = {
    "public-bucket": {
        "title": "Public storage exposure",
        "impact": "Anyone on the internet can list and download the "
                  "objects — no credentials, no logging of who took what. "
                  "Backups and exports usually contain customer PII, "
                  "credentials and payment data.",
        "context": "Misconfigured public buckets are behind some of the "
                   "largest breaches ever disclosed; scanners find newly "
                   "public buckets within minutes.",
        "fix": "Make the bucket private, enable at-rest encryption, and "
               "keep truly public content in a dedicated bucket.",
    },
    "over-permissive-iam": {
        "title": "Over-permissive IAM role",
        "impact": "One phished developer password becomes full account "
                  "takeover: the attacker inherits every permission the "
                  "account holds, including deleting backups and locking "
                  "you out.",
        "context": "\"Temporary\" admin grants during incidents are the "
                   "classic source — they are rarely revoked afterwards.",
        "fix": "Detach the admin role, keep the role that matches the "
               "job, and verify with a permission simulation.",
    },
    "open-ssh": {
        "title": "SSH open to the internet",
        "impact": "Port 22 on 0.0.0.0/0 invites continuous brute-force "
                  "and credential-stuffing from the whole internet; one "
                  "weak key or password yields a shell inside your VPC.",
        "context": "Internet-wide scanners hit a newly opened port 22 "
                   "within minutes. \"Quick debugging\" rules have a way "
                   "of becoming permanent.",
        "fix": "Revoke the world-open rule; allow SSH only from your "
               "office/VPN range, or better, use a bastion.",
    },
    "public-database": {
        "title": "Database exposed publicly",
        "impact": "The crown jewels answer connections from anywhere. "
                  "Attackers need only credentials — or an unpatched "
                  "engine bug — to read or ransom the entire dataset.",
        "context": "Exposed databases are ransomed in automated campaigns "
                   "that wipe data and leave a payment note.",
        "fix": "Disable the public endpoint AND revoke the world-open "
               "port rule — either one alone leaves a path.",
    },
    "weak-password-policy": {
        "title": "Weak password policy",
        "impact": "Short passwords without MFA fall to credential "
                  "stuffing and spraying; a single reused password can "
                  "open the cloud console.",
        "context": "Password spraying stays under lockout thresholds by "
                   "trying one common password across many accounts.",
        "fix": f"Require at least {BASELINE_MIN_LENGTH} characters and "
               f"enforce MFA for every user.",
    },
    "unused-admin": {
        "title": "Unused administrator account",
        "impact": "A dormant admin identity nobody watches — with an "
                  "active API key, it is a skeleton key waiting to leak. "
                  "Departed-employee accounts are prime targets.",
        "context": "Off-boarding gaps are consistently among the top "
                   "audit findings; stale keys turn up in old laptops "
                   "and code repos.",
        "fix": "Disable the account and deactivate its access key; "
               "review remaining admins regularly.",
    },
}


# ===========================================================================
# Password policy
# ===========================================================================
def policy_strong(policy: dict[str, Any]) -> bool:
    return int(policy.get("min_length", 0)) >= BASELINE_MIN_LENGTH and \
        bool(policy.get("mfa_required", False))


def format_password_policy(policy: dict[str, Any]) -> str:
    strong = policy_strong(policy)
    lines = [
        "ACCOUNT PASSWORD POLICY",
        "─" * 40,
        f"  Minimum length:    {policy.get('min_length', 0)}"
        + ("" if int(policy.get('min_length', 0)) >= BASELINE_MIN_LENGTH
           else f"   ⚠ baseline is {BASELINE_MIN_LENGTH}"),
        f"  Require numbers:   "
        f"{'yes' if policy.get('require_numbers') else 'no'}",
        f"  Require symbols:   "
        f"{'yes' if policy.get('require_symbols') else 'no'}",
        f"  MFA required:      "
        f"{'yes' if policy.get('mfa_required') else 'NO   ⚠'}",
        f"  Max password age:  "
        f"{policy.get('max_age_days') or 'not set'}",
        "─" * 40,
        "  Posture: " + ("✔ meets baseline" if strong
                         else "✖ BELOW BASELINE — see "
                              "`risk weak-password-policy`"),
    ]
    return "\n".join(lines)


def update_policy(policy: dict[str, Any], setting: str,
                  value: str) -> OpResult:
    setting = (setting or "").strip().lower().replace("_", "-")
    value = (value or "").strip().lower()
    if setting == "min-length":
        try:
            length = int(value)
        except ValueError:
            return OpResult(False, "min-length needs a number, e.g. "
                                   "`set-password-policy min-length 14`.")
        if length < 4 or length > 128:
            return OpResult(False, "Choose a length between 4 and 128.")
        policy["min_length"] = length
    elif setting in ("require-mfa", "mfa"):
        if value not in ("on", "off"):
            return OpResult(False, "Use on/off, e.g. "
                                   "`set-password-policy require-mfa on`.")
        policy["mfa_required"] = value == "on"
    elif setting == "require-numbers":
        policy["require_numbers"] = value == "on"
    elif setting == "require-symbols":
        policy["require_symbols"] = value == "on"
    else:
        return OpResult(False, "Settings: min-length, require-mfa, "
                               "require-numbers, require-symbols.")
    strong = policy_strong(policy)
    return OpResult(
        True,
        f"✔ Policy updated.\n\n{format_password_policy(policy)}",
        events=[{"type": "policy_updated", "setting": setting,
                 "strong": strong}])


# ===========================================================================
# Risk library
# ===========================================================================
def format_risk(topic: str) -> OpResult:
    topic = (topic or "").strip().lower()
    risk = RISKS.get(topic)
    if risk is None:
        topics = "\n  · ".join(sorted(RISKS))
        return OpResult(False, f"Unknown risk topic. Available:\n"
                               f"  · {topics}")
    message = (f"RISK BRIEF — {risk['title']}\n"
               f"{'─' * 50}\n"
               f" IMPACT\n   {risk['impact']}\n\n"
               f" REAL WORLD\n   {risk['context']}\n\n"
               f" THE FIX\n   {risk['fix']}")
    return OpResult(True, message,
                    events=[{"type": "risk_reviewed", "topic": topic}])
