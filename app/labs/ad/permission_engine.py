"""Permission Engine (YC-031.0) — who can access what, and why.

Two responsibilities:

  · Share access resolution — effective rights on a shared folder from
    a user's group memberships, always with the *reason* (which ACL
    entry granted it), because "why does the intern read HR files?" is
    the entire pedagogical point.
  · The conceptual Kerberos ticket flow — a step-by-step visualisation
    of AS-REQ → TGT → TGS → service ticket → access decision, including
    the realistic failure branches (disabled account, locked account).

Pure functions; ACL mutation (grant/revoke) also lives here since ACLs
are permission data.
"""

from __future__ import annotations

from typing import Any, Optional

from app.labs.ad import engine
from app.labs.ad.user_engine import OpResult

_RIGHT_ORDER = {"read": 1, "write": 2, "full": 3}


# ---------------------------------------------------------------------------
# Effective access
# ---------------------------------------------------------------------------
def effective_access(directory: dict[str, Any], user: dict[str, Any],
                     share: dict[str, Any]) -> tuple[Optional[str], list[dict[str, Any]]]:
    """The strongest right the user holds on the share, plus every ACL
    entry that applied. Returns (right | None, matched_entries)."""
    matched = [entry for entry in share.get("acl", [])
               if entry.get("group") in user.get("groups", [])]
    if not matched:
        return None, []
    best = max(matched, key=lambda e: _RIGHT_ORDER.get(e.get("right"), 0))
    return best.get("right"), matched


def check_access(directory: dict[str, Any], user_key: str,
                 share_key: str) -> OpResult:
    user = engine.find_user(directory, user_key)
    if user is None:
        return OpResult(False, f"Cannot find user '{user_key}'.")
    share = engine.find_share(directory, share_key)
    if share is None:
        return OpResult(False, f"Cannot find shared folder '{share_key}'. "
                               f"Run `get-shares` to list them.")

    if not user["enabled"] or user["locked"]:
        why = "disabled" if not user["enabled"] else "locked out"
        return OpResult(
            True,
            f"ACCESS DENIED — '{user['sam']}' cannot authenticate: the "
            f"account is {why}.\n(No Kerberos ticket → no access, whatever "
            f"the ACL says.)",
            events=[{"type": "access_checked", "sam": user["sam"],
                     "share": share["slug"], "allowed": False,
                     "reason": why}],
        )

    right, matched = effective_access(directory, user, share)
    if right is None:
        return OpResult(
            True,
            f"ACCESS DENIED — '{user['sam']}' holds no rights on "
            f"'{share['name']}' ({share['path']}).\nNo ACL entry matches "
            f"any of their groups.",
            events=[{"type": "access_checked", "sam": user["sam"],
                     "share": share["slug"], "allowed": False,
                     "reason": "no_acl_match"}],
        )

    reasons = "\n".join(
        f"  · via group '{directory['groups'].get(e['group'], {}).get('name', e['group'])}'"
        f" → {e['right'].upper()}"
        for e in matched
    )
    warn = ""
    if share["slug"] == "hr-confidential" and any(
            e["group"] == "domain-users" for e in matched):
        warn = ("\n⚠ AUDIT FINDING: this access comes from 'Domain Users' — "
                "EVERY account in the domain can read this confidential "
                "share. That violates least privilege.")
    return OpResult(
        True,
        f"ACCESS GRANTED — '{user['sam']}' has {right.upper()} on "
        f"'{share['name']}' ({share['path']}).\n{reasons}{warn}",
        events=[{"type": "access_checked", "sam": user["sam"],
                 "share": share["slug"], "allowed": True, "right": right,
                 "via_domain_users": any(e["group"] == "domain-users"
                                         for e in matched)}],
    )


# ---------------------------------------------------------------------------
# ACL management
# ---------------------------------------------------------------------------
def grant_access(directory: dict[str, Any], share_key: str, group_key: str,
                 right: str) -> OpResult:
    share = engine.find_share(directory, share_key)
    if share is None:
        return OpResult(False, f"Cannot find shared folder '{share_key}'.")
    group = engine.find_group(directory, group_key)
    if group is None:
        return OpResult(False, f"Cannot find group '{group_key}'.")
    right = (right or "").lower()
    if right not in _RIGHT_ORDER:
        return OpResult(False, "Right must be one of: read, write, full.")

    for entry in share["acl"]:
        if entry["group"] == group["slug"]:
            entry["right"] = right
            break
    else:
        share["acl"].append({"group": group["slug"], "right": right})
    return OpResult(
        True,
        f"Granted {right.upper()} on '{share['name']}' to "
        f"'{group['name']}'.",
        events=[{"type": "access_granted", "share": share["slug"],
                 "group": group["slug"], "right": right}],
    )


def revoke_access(directory: dict[str, Any], share_key: str,
                  group_key: str) -> OpResult:
    share = engine.find_share(directory, share_key)
    if share is None:
        return OpResult(False, f"Cannot find shared folder '{share_key}'.")
    group = engine.find_group(directory, group_key)
    if group is None:
        return OpResult(False, f"Cannot find group '{group_key}'.")

    before = len(share["acl"])
    share["acl"] = [e for e in share["acl"] if e["group"] != group["slug"]]
    if len(share["acl"]) == before:
        return OpResult(True,
                        f"'{group['name']}' holds no rights on "
                        f"'{share['name']}' — nothing to revoke.",
                        events=[{"type": "access_revoked",
                                 "share": share["slug"],
                                 "group": group["slug"], "changed": False}])
    return OpResult(
        True,
        f"Revoked all rights of '{group['name']}' on '{share['name']}'.\n"
        f"✓ Access is now limited to the remaining ACL entries.",
        events=[{"type": "access_revoked", "share": share["slug"],
                 "group": group["slug"], "changed": True}],
    )


def format_share(directory: dict[str, Any], share: dict[str, Any]) -> str:
    acl = "\n".join(
        f"  · {directory['groups'].get(e['group'], {}).get('name', e['group']):<16}"
        f" {e['right'].upper()}"
        + ("   ⚠ everyone in the domain" if e["group"] == "domain-users"
           and share["slug"] != "public" else "")
        for e in share.get("acl", [])
    ) or "  (empty ACL — no one has access)"
    return (
        f"Share       : {share['name']}\n"
        f"Path        : {share['path']}\n"
        f"Server      : {share['server']}\n"
        f"Description : {share.get('description') or '—'}\n"
        f"Permissions :\n{acl}"
    )


def format_share_table(directory: dict[str, Any]) -> str:
    rows = ["SHARE                PATH                          ACL ENTRIES",
            "─" * 62]
    for slug in sorted(directory.get("shares", {})):
        share = directory["shares"][slug]
        rows.append(f"{share['name']:<20} {share['path']:<29} "
                    f"{len(share.get('acl', []))}")
    rows.append("")
    rows.append("Use `get-share <name>` for the full permission list, and "
                "`access <user> <share>` to test access.")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Kerberos — the conceptual ticket flow
# ---------------------------------------------------------------------------
def kerberos_flow(directory: dict[str, Any], user_key: str,
                  service: str = "") -> OpResult:
    """Step-by-step conceptual Kerberos authentication for one user.

    Not a protocol implementation — an educational walkthrough with the
    branches students must recognise: disabled and locked accounts are
    refused a TGT by the KDC, which is exactly why disabling a
    compromised account works."""
    user = engine.find_user(directory, user_key)
    if user is None:
        return OpResult(False, f"Cannot find user '{user_key}'.")

    dc = next((c for c in directory.get("computers", {}).values()
               if c.get("is_dc")), {"name": "DC"})
    service = service or "cifs/FS-01"
    steps = [f"KERBEROS AUTHENTICATION — {user['display']} "
             f"({directory['domain'].get('name', 'DOMAIN')})",
             "─" * 56,
             f"[1] AS-REQ   {user['sam']} → {dc['name']} (KDC): "
             f"\"I am {user['sam']}, here is proof (encrypted timestamp)\""]

    if not user["enabled"]:
        steps += [f"[2] AS-REP   {dc['name']} → KDC_ERR_CLIENT_REVOKED",
                  "",
                  "✗ REFUSED — the account is DISABLED. The KDC never "
                  "issues a TGT, so no service in the domain will accept "
                  "this user. This is why disabling beats deleting during "
                  "an incident: access dies instantly, evidence survives."]
        return OpResult(True, "\n".join(steps),
                        events=[{"type": "kerberos_viewed",
                                 "sam": user["sam"], "ok": False,
                                 "reason": "disabled"}])
    if user["locked"]:
        steps += [f"[2] AS-REP   {dc['name']} → KDC_ERR_CLIENT_REVOKED",
                  "",
                  "✗ REFUSED — the account is LOCKED OUT "
                  f"({user.get('failed_attempts', 0)} failed attempts). "
                  "The lockout policy is doing its job; unlock only after "
                  "confirming the owner is in control of the credentials."]
        return OpResult(True, "\n".join(steps),
                        events=[{"type": "kerberos_viewed",
                                 "sam": user["sam"], "ok": False,
                                 "reason": "locked"}])

    steps += [
        f"[2] AS-REP   {dc['name']} → {user['sam']}: "
        f"TGT (Ticket-Granting Ticket), valid 10h",
        f"[3] TGS-REQ  {user['sam']} → {dc['name']}: "
        f"\"here is my TGT — I need a ticket for {service}\"",
        f"[4] TGS-REP  {dc['name']} → {user['sam']}: "
        f"service ticket for {service}",
        f"[5] AP-REQ   {user['sam']} → {service.split('/')[-1]}: "
        f"presents the service ticket",
        "[6] ACCESS   the SERVER now checks its ACL against the user's "
        "group SIDs carried in the ticket",
        "",
        "✓ Authentication succeeded. Note the separation of duties:",
        "  · the KDC proves WHO you are (authentication)",
        "  · the resource's ACL decides WHAT you may do (authorization)",
        f"Run `access {user['sam']} <share>` to see step [6] in action.",
    ]
    return OpResult(True, "\n".join(steps),
                    events=[{"type": "kerberos_viewed", "sam": user["sam"],
                             "ok": True}])
