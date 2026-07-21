"""User Engine (YC-031.0) — account lifecycle operations.

Every operation is a pure function:  (directory, args) -> OpResult.
The directory passed in is mutated *in place* — it is already the
session's private copy (the simulator deep-copies nothing because the
whole envelope is per-user session state, never shared).

OpResult carries the terminal message AND the events the objective
engine validates against, so seeds can hang objectives off precise
signals (``password_reset`` with ``policy_ok=True``) instead of string
matching output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.labs.ad import engine, policy_engine


@dataclass
class OpResult:
    ok: bool
    message: str
    events: list[dict[str, Any]] = field(default_factory=list)


def _no_user(key: str) -> OpResult:
    return OpResult(False, f"Get-ADUser : Cannot find an object with identity: '{key}'.")


# ---------------------------------------------------------------------------
# Account operations
# ---------------------------------------------------------------------------
def reset_password(directory: dict[str, Any], key: str,
                   new_password: str) -> OpResult:
    """Reset a user's password — enforced against the domain password
    policy, exactly like a real DC would."""
    user = engine.find_user(directory, key)
    if user is None:
        return _no_user(key)

    ok, problems = policy_engine.check_password(directory, user["sam"],
                                                new_password)
    if not ok:
        detail = "\n".join(f"  ✗ {p}" for p in problems)
        return OpResult(
            False,
            f"Set-ADAccountPassword : password for '{user['sam']}' REJECTED "
            f"by policy:\n{detail}\n\nRun `policy` to review the requirements.",
            events=[{"type": "password_reset", "sam": user["sam"],
                     "policy_ok": False}],
        )

    user["password_set"] = True
    user["failed_attempts"] = 0
    return OpResult(
        True,
        f"Password for '{user['sam']}' ({user['display']}) reset "
        f"successfully — meets the domain password policy.\n"
        f"The user must change it at next logon."
        + ("\n\nNOTE: the account is still LOCKED — run "
           f"`unlock {user['sam']}` to restore access." if user["locked"] else ""),
        events=[{"type": "password_reset", "sam": user["sam"],
                 "policy_ok": True}],
    )


def unlock_account(directory: dict[str, Any], key: str) -> OpResult:
    user = engine.find_user(directory, key)
    if user is None:
        return _no_user(key)
    if not user["locked"]:
        return OpResult(True, f"Account '{user['sam']}' is not locked.",
                        events=[{"type": "account_unlocked",
                                 "sam": user["sam"], "was_locked": False}])
    user["locked"] = False
    user["failed_attempts"] = 0
    return OpResult(
        True,
        f"Account '{user['sam']}' ({user['display']}) UNLOCKED.\n"
        f"Failed-attempt counter reset to 0.",
        events=[{"type": "account_unlocked", "sam": user["sam"],
                 "was_locked": True}],
    )


def set_enabled(directory: dict[str, Any], key: str, enabled: bool) -> OpResult:
    user = engine.find_user(directory, key)
    if user is None:
        return _no_user(key)
    verb = "ENABLED" if enabled else "DISABLED"
    if user["enabled"] == enabled:
        return OpResult(True, f"Account '{user['sam']}' is already {verb.lower()}.",
                        events=[{"type": "account_enabled" if enabled
                                 else "account_disabled",
                                 "sam": user["sam"], "changed": False}])
    user["enabled"] = enabled
    extra = ""
    if not enabled:
        extra = ("\nExisting Kerberos tickets will expire; no new logons "
                 "are possible.")
    return OpResult(
        True,
        f"Account '{user['sam']}' ({user['display']}) {verb}.{extra}",
        events=[{"type": "account_enabled" if enabled else "account_disabled",
                 "sam": user["sam"], "changed": True}],
    )


def move_user(directory: dict[str, Any], key: str, ou_key: str) -> OpResult:
    user = engine.find_user(directory, key)
    if user is None:
        return _no_user(key)
    ou = engine.find_ou(directory, ou_key)
    if ou is None:
        return OpResult(False,
                        f"Move-ADObject : Cannot find OU '{ou_key}'. "
                        f"Run `get-ous` to list the organizational units.")
    if user["ou"] == ou["slug"]:
        return OpResult(True,
                        f"'{user['sam']}' is already in OU '{ou['name']}'.",
                        events=[{"type": "user_moved", "sam": user["sam"],
                                 "ou": ou["slug"], "changed": False}])
    previous = user["ou"]
    user["ou"] = ou["slug"]
    return OpResult(
        True,
        f"Moved '{user['sam']}' ({user['display']}) from OU "
        f"'{directory['ous'].get(previous, {}).get('name', previous)}' "
        f"to OU '{ou['name']}'.",
        events=[{"type": "user_moved", "sam": user["sam"],
                 "ou": ou["slug"], "from": previous, "changed": True}],
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def format_user(directory: dict[str, Any], user: dict[str, Any]) -> str:
    ou = directory.get("ous", {}).get(user.get("ou", ""), {})
    group_names = [directory["groups"][g]["name"]
                   for g in user.get("groups", [])
                   if g in directory.get("groups", {})]
    status = []
    status.append("Enabled" if user["enabled"] else "DISABLED")
    if user["locked"]:
        status.append("LOCKED OUT")
    if user.get("service_account"):
        status.append("service account")
    logon = user.get("last_logon_days", 0)
    logon_str = "today" if logon == 0 else f"{logon} day(s) ago"
    warn = "  ⚠ INACTIVE" if logon >= 90 else ""
    admin_flag = ("\n  ⚠ MEMBER OF DOMAIN ADMINS"
                  if "domain-admins" in user.get("groups", []) else "")
    return (
        f"User          : {user['display']}\n"
        f"sAMAccountName: {user['sam']}\n"
        f"Title         : {user.get('title') or '—'}\n"
        f"OU            : {ou.get('name', user.get('ou') or '—')}\n"
        f"Status        : {', '.join(status)}\n"
        f"Failed logons : {user.get('failed_attempts', 0)}\n"
        f"Last logon    : {logon_str}{warn}\n"
        f"Member of     : {', '.join(group_names) or '—'}{admin_flag}\n"
        f"Description   : {user.get('description') or '—'}"
    )


def format_user_table(directory: dict[str, Any]) -> str:
    rows = ["SAM             DISPLAY NAME             OU            STATUS      LAST LOGON",
            "─" * 78]
    for sam in sorted(directory.get("users", {})):
        user = directory["users"][sam]
        ou = directory.get("ous", {}).get(user.get("ou", ""), {})
        status = "disabled" if not user["enabled"] else (
            "LOCKED" if user["locked"] else "ok")
        logon = user.get("last_logon_days", 0)
        logon_str = "today" if logon == 0 else f"{logon}d ago"
        if logon >= 90:
            logon_str += " ⚠"
        rows.append(f"{sam:<15} {user['display']:<24} "
                    f"{ou.get('name', '—'):<13} {status:<11} {logon_str}")
    rows.append("")
    rows.append(f"{len(directory.get('users', {}))} user(s). "
                f"Use `get-user <sam>` for details.")
    return "\n".join(rows)
