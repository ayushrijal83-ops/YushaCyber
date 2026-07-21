"""Group Engine (YC-031.0) — membership queries + management.

Pure functions over the session directory, same contract as the User
Engine. Privileged-group awareness lives here so every current and
future lab shares one definition of "this membership is dangerous".
"""

from __future__ import annotations

from typing import Any

from app.labs.ad import engine
from app.labs.ad.user_engine import OpResult

#: Groups whose membership constitutes elevated privilege. Future labs
#: (Kerberoasting awareness, tiered-admin design) extend this set.
PRIVILEGED_GROUPS = {"domain-admins"}


def _no_group(key: str) -> OpResult:
    return OpResult(False,
                    f"Get-ADGroup : Cannot find an object with identity: '{key}'.")


def add_member(directory: dict[str, Any], group_key: str,
               user_key: str) -> OpResult:
    group = engine.find_group(directory, group_key)
    if group is None:
        return _no_group(group_key)
    user = engine.find_user(directory, user_key)
    if user is None:
        return OpResult(False,
                        f"Add-ADGroupMember : Cannot find user '{user_key}'.")

    if user["sam"] in group["members"]:
        return OpResult(True,
                        f"'{user['sam']}' is already a member of "
                        f"'{group['name']}'.",
                        events=[{"type": "member_added", "group": group["slug"],
                                 "sam": user["sam"], "changed": False}])

    group["members"].append(user["sam"])
    user["groups"].append(group["slug"])
    warning = ""
    if group["slug"] in PRIVILEGED_GROUPS:
        warning = ("\n⚠ WARNING: this grants FULL administrative control of "
                   "the domain. Verify this is intended and documented.")
    return OpResult(
        True,
        f"Added '{user['sam']}' ({user['display']}) to '{group['name']}'."
        f"{warning}",
        events=[{"type": "member_added", "group": group["slug"],
                 "sam": user["sam"], "changed": True,
                 "privileged": group["slug"] in PRIVILEGED_GROUPS}],
    )


def remove_member(directory: dict[str, Any], group_key: str,
                  user_key: str) -> OpResult:
    group = engine.find_group(directory, group_key)
    if group is None:
        return _no_group(group_key)
    user = engine.find_user(directory, user_key)
    if user is None:
        return OpResult(False,
                        f"Remove-ADGroupMember : Cannot find user '{user_key}'.")

    if user["sam"] not in group["members"]:
        return OpResult(True,
                        f"'{user['sam']}' is not a member of '{group['name']}'.",
                        events=[{"type": "member_removed",
                                 "group": group["slug"], "sam": user["sam"],
                                 "changed": False}])

    if group["slug"] == "domain-users":
        return OpResult(False,
                        "Remove-ADGroupMember : refusing to remove a user "
                        "from 'Domain Users' — it is the primary group of "
                        "every account.")

    group["members"].remove(user["sam"])
    if group["slug"] in user["groups"]:
        user["groups"].remove(group["slug"])
    note = ""
    if group["slug"] in PRIVILEGED_GROUPS:
        note = "\n✓ Least privilege restored — one fewer domain administrator."
    return OpResult(
        True,
        f"Removed '{user['sam']}' ({user['display']}) from "
        f"'{group['name']}'.{note}",
        events=[{"type": "member_removed", "group": group["slug"],
                 "sam": user["sam"], "changed": True,
                 "privileged": group["slug"] in PRIVILEGED_GROUPS}],
    )


# ---------------------------------------------------------------------------
# Analysis + formatting
# ---------------------------------------------------------------------------
def overprivileged_members(directory: dict[str, Any]) -> list[dict[str, Any]]:
    """Members of privileged groups whose role does not look administrative
    — the engine flags interns, service accounts and non-IT staff. Used by
    labs and by the admin scenario preview."""
    flagged: list[dict[str, Any]] = []
    for slug in PRIVILEGED_GROUPS:
        group = directory.get("groups", {}).get(slug)
        if group is None:
            continue
        for sam in group["members"]:
            user = directory["users"].get(sam)
            if user is None:
                continue
            suspicious = (
                user.get("ou") in {"interns", "service-accounts"}
                or user.get("service_account", False)
                or "intern" in (user.get("title", "") + user.get("display", "")).lower()
            )
            if suspicious:
                flagged.append({"sam": sam, "group": slug,
                                "reason": user.get("title") or user.get("ou")})
    return flagged


def format_group(directory: dict[str, Any], group: dict[str, Any]) -> str:
    members = []
    for sam in sorted(group["members"]):
        user = directory["users"].get(sam, {})
        marker = ""
        if group["slug"] in PRIVILEGED_GROUPS and (
                user.get("ou") in {"interns", "service-accounts"}
                or "intern" in user.get("title", "").lower()):
            marker = "   ⚠ review — least privilege?"
        members.append(f"  · {sam:<14} {user.get('display', '?')}"
                       f"{marker}")
    body = "\n".join(members) if members else "  (no members)"
    kind = "Built-in" if group.get("builtin") else "Custom"
    privileged = ("\n⚠ PRIVILEGED GROUP — members have administrative "
                  "control. Keep membership minimal."
                  if group["slug"] in PRIVILEGED_GROUPS else "")
    return (
        f"Group       : {group['name']}  ({kind})\n"
        f"Description : {group.get('description') or '—'}\n"
        f"Members     : {len(group['members'])}{privileged}\n"
        f"{body}"
    )


def format_group_table(directory: dict[str, Any]) -> str:
    rows = ["GROUP                    KIND      MEMBERS",
            "─" * 46]
    for slug in sorted(directory.get("groups", {})):
        group = directory["groups"][slug]
        kind = "built-in" if group.get("builtin") else "custom"
        flag = "  ⚠" if slug in PRIVILEGED_GROUPS else ""
        rows.append(f"{group['name']:<24} {kind:<9} "
                    f"{len(group['members'])}{flag}")
    rows.append("")
    rows.append("Use `get-group <name>` or `members <name>` for membership.")
    return "\n".join(rows)
