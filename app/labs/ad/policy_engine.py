"""Policy Engine (YC-031.0) — Group Policy simulation.

Pure functions over a directory. Owns:

  · the effective password policy + validating candidate passwords
  · the account lockout policy + the lockout counter model
  · rendering GPOs (desktop restrictions, login scripts) for display

Reused by the User Engine (password resets must pass policy) and the
Permission Engine (a locked/disabled account never authenticates).
"""

from __future__ import annotations

from typing import Any

_DEFAULT_PASSWORD_POLICY = {"min_length": 8, "complexity": True,
                            "max_age_days": 90, "history": 3}
_DEFAULT_LOCKOUT_POLICY = {"threshold": 5, "duration_minutes": 30,
                           "window_minutes": 15}


def get_password_policy(directory: dict[str, Any]) -> dict[str, Any]:
    """The effective password policy: first GPO that defines one wins
    (Default Domain Policy by convention), else safe defaults."""
    for gpo in directory.get("gpos", {}).values():
        policy = gpo.get("password_policy")
        if policy:
            return {**_DEFAULT_PASSWORD_POLICY, **policy}
    return dict(_DEFAULT_PASSWORD_POLICY)


def get_lockout_policy(directory: dict[str, Any]) -> dict[str, Any]:
    for gpo in directory.get("gpos", {}).values():
        policy = gpo.get("lockout_policy")
        if policy:
            return {**_DEFAULT_LOCKOUT_POLICY, **policy}
    return dict(_DEFAULT_LOCKOUT_POLICY)


def check_password(directory: dict[str, Any], sam: str,
                   candidate: str) -> tuple[bool, list[str]]:
    """Validate a candidate password against the effective policy.

    Returns (ok, problems). Complexity means at least 3 of the 4
    character classes (upper, lower, digit, symbol) and the password
    must not contain the account name — the same rules Windows teaches.
    """
    policy = get_password_policy(directory)
    problems: list[str] = []
    candidate = candidate or ""

    if len(candidate) < int(policy["min_length"]):
        problems.append(
            f"too short — policy requires at least {policy['min_length']} "
            f"characters (got {len(candidate)})")

    if policy.get("complexity"):
        classes = sum([
            any(c.isupper() for c in candidate),
            any(c.islower() for c in candidate),
            any(c.isdigit() for c in candidate),
            any(not c.isalnum() for c in candidate),
        ])
        if classes < 3:
            problems.append(
                "not complex enough — needs at least 3 of: uppercase, "
                "lowercase, digits, symbols")
        if sam and sam.lower() in candidate.lower():
            problems.append("must not contain the account name")

    return (len(problems) == 0), problems


def format_password_policy(directory: dict[str, Any]) -> str:
    policy = get_password_policy(directory)
    lockout = get_lockout_policy(directory)
    return (
        "PASSWORD POLICY (Default Domain Policy)\n"
        f"  Minimum length      : {policy['min_length']} characters\n"
        f"  Complexity required : {'Yes — 3 of 4 character classes' if policy.get('complexity') else 'No'}\n"
        f"  Maximum age         : {policy.get('max_age_days', '—')} days\n"
        f"  Password history    : last {policy.get('history', '—')} remembered\n"
        "\n"
        "ACCOUNT LOCKOUT POLICY\n"
        f"  Lockout threshold   : {lockout['threshold']} failed attempts\n"
        f"  Observation window  : {lockout.get('window_minutes', '—')} minutes\n"
        f"  Lockout duration    : {lockout.get('duration_minutes', '—')} minutes"
    )


def format_gpo(gpo: dict[str, Any]) -> str:
    """Render one GPO for terminal display."""
    lines = [f"GPO: {gpo.get('name', gpo.get('slug', '?'))}",
             f"  Linked to : {', '.join(gpo.get('linked_to', [])) or '—'}",
             f"  Kind      : {gpo.get('kind', 'general')}"]
    if gpo.get("password_policy"):
        pw = gpo["password_policy"]
        lines.append(f"  Password  : min {pw.get('min_length')} chars, "
                     f"complexity {'on' if pw.get('complexity') else 'off'}, "
                     f"max age {pw.get('max_age_days')}d")
    if gpo.get("lockout_policy"):
        lock = gpo["lockout_policy"]
        lines.append(f"  Lockout   : {lock.get('threshold')} attempts / "
                     f"{lock.get('window_minutes')}min window / "
                     f"{lock.get('duration_minutes')}min lock")
    if gpo.get("script"):
        lines.append(f"  Script    : {gpo['script']}")
    for key, value in (gpo.get("settings") or {}).items():
        lines.append(f"  {key.replace('_', ' ').title():<10}: {value}")
    return "\n".join(lines)


def list_gpos(directory: dict[str, Any]) -> str:
    gpos = sorted(directory.get("gpos", {}).values(), key=lambda g: g["slug"])
    if not gpos:
        return "No Group Policy Objects defined."
    return "\n\n".join(format_gpo(g) for g in gpos)
