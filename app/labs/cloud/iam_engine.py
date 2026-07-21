"""IAM Engine (YC-032.0) — identities, roles and permission evaluation.

Reusable, provider-agnostic identity operations. Events carry the
facts validators need (usernames, roles, computed flags) so the
Objective Engine stays untouched.
"""

from __future__ import annotations

from typing import Any

from app.labs.cloud.engine import OpResult, _user_is_admin, find_role, \
    find_user


# ===========================================================================
# Formatting
# ===========================================================================
def format_user_table(deployment: dict) -> str:
    lines = [f"{'USERNAME':<14}{'ROLES':<28}{'MFA':<5}{'KEY':<9}"
             f"{'LAST USED':<12}STATUS"]
    lines.append("─" * 76)
    for user in deployment.get("users", {}).values():
        marks = []
        if _user_is_admin(deployment, user) and \
                user["expected_role"] != "administrator":
            marks.append("⚠ excessive")
        if _user_is_admin(deployment, user) and \
                user["last_used_days"] >= 90:
            marks.append("⚠ stale admin")
        status = "disabled" if not user["enabled"] else \
            (" ".join(marks) or "ok")
        lines.append(
            f"{user['username']:<14}{','.join(user['roles']):<28}"
            f"{'yes' if user['mfa'] else 'NO':<5}"
            f"{'active' if user['access_key_active'] else 'off':<9}"
            f"{str(user['last_used_days']) + 'd ago':<12}{status}")
    return "\n".join(lines)


def format_user(deployment: dict, user: dict) -> str:
    admin = _user_is_admin(deployment, user)
    excessive = admin and user["expected_role"] != "administrator"
    stale_admin = admin and user["enabled"] and \
        user["last_used_days"] >= 90
    lines = [
        f"IAM USER: {user['username']}  ({user['display']})",
        f"  Status:       "
        f"{'enabled' if user['enabled'] else 'DISABLED'}",
        f"  Roles:        {', '.join(user['roles']) or '—'}",
        f"  Expected:     {user['expected_role'] or '—'}",
        f"  MFA:          {'enabled' if user['mfa'] else 'NOT ENABLED'}",
        f"  Access key:   "
        f"{'ACTIVE' if user['access_key_active'] else 'deactivated'}",
        f"  Last used:    {user['last_used_days']} day(s) ago",
        f"  {user['description']}",
    ]
    if excessive:
        lines.append("  ⚠ FINDING: holds Administrator beyond their "
                     "expected role — least-privilege violation.")
    if stale_admin:
        lines.append("  ⚠ FINDING: administrator account unused for 90+ "
                     "days — off-board or disable it.")
    return "\n".join(lines)


def format_role_table(deployment: dict) -> str:
    lines = [f"{'ROLE':<16}{'PERMISSIONS':<38}NOTE"]
    lines.append("─" * 70)
    for role in deployment.get("roles", {}).values():
        note = "⚠ full control" if "*:*" in role["permissions"] else ""
        lines.append(f"{role['slug']:<16}"
                     f"{', '.join(role['permissions']):<38}{note}")
    return "\n".join(lines)


def format_role(deployment: dict, role: dict) -> str:
    members = [u["username"] for u in deployment.get("users", {}).values()
               if role["slug"] in u["roles"]]
    lines = [
        f"IAM ROLE: {role['name']}  ({role['slug']})",
        f"  {role['description']}",
        f"  Permissions: {', '.join(role['permissions'])}",
        f"  Attached to: {', '.join(members) or '—'}",
    ]
    if "*:*" in role["permissions"]:
        lines.append("  ⚠ Grants full control — attach only to break-glass "
                     "administrators.")
    return "\n".join(lines)


# ===========================================================================
# Operations
# ===========================================================================
def create_user(deployment: dict, username: str, role_ref: str) -> OpResult:
    username = (username or "").strip().lower()
    if not username or not username.replace("-", "").isalnum():
        return OpResult(False, "Usernames are lowercase letters, digits "
                               "and hyphens.")
    if username in deployment.get("users", {}):
        return OpResult(False, f"User '{username}' already exists.")
    role = find_role(deployment, role_ref)
    if role is None:
        return OpResult(False, f"Unknown role '{role_ref}'. See "
                               f"`list-roles`.")
    deployment["users"][username] = {
        "username": username, "display": username, "roles": [role["slug"]],
        "expected_role": role["slug"], "mfa": False,
        "access_key_active": False, "last_used_days": 0,
        "enabled": True, "description": "Created in this session.",
    }
    return OpResult(
        True,
        f"✔ IAM user '{username}' created with role '{role['slug']}'.\n"
        f"  Enable MFA before issuing access keys.",
        events=[{"type": "iam_user_created", "username": username,
                 "role": role["slug"]}])


def attach_role(deployment: dict, user_ref: str, role_ref: str) -> OpResult:
    user = find_user(deployment, user_ref)
    if user is None:
        return OpResult(False, f"Unknown user '{user_ref}'.")
    role = find_role(deployment, role_ref)
    if role is None:
        return OpResult(False, f"Unknown role '{role_ref}'.")
    if role["slug"] in user["roles"]:
        return OpResult(False, f"'{user['username']}' already has role "
                               f"'{role['slug']}'.")
    user["roles"].append(role["slug"])
    admin = "*:*" in role["permissions"]
    warning = ("\n  ⚠ You just granted FULL CONTROL — make sure that is "
               "intentional." if admin else "")
    return OpResult(
        True,
        f"✔ Role '{role['slug']}' attached to '{user['username']}'."
        f"{warning}",
        events=[{"type": "iam_role_attached", "username": user["username"],
                 "role": role["slug"], "admin": admin}])


def detach_role(deployment: dict, user_ref: str, role_ref: str) -> OpResult:
    user = find_user(deployment, user_ref)
    if user is None:
        return OpResult(False, f"Unknown user '{user_ref}'.")
    role = find_role(deployment, role_ref)
    if role is None:
        return OpResult(False, f"Unknown role '{role_ref}'.")
    if role["slug"] not in user["roles"]:
        return OpResult(False, f"'{user['username']}' does not have role "
                               f"'{role['slug']}'.")
    if len(user["roles"]) == 1:
        return OpResult(False, "A user needs at least one role — attach "
                               "the correct role first.")
    user["roles"].remove(role["slug"])
    return OpResult(
        True,
        f"✔ Role '{role['slug']}' detached from '{user['username']}'.\n"
        f"  Remaining roles: {', '.join(user['roles'])}",
        events=[{"type": "iam_role_detached", "username": user["username"],
                 "role": role["slug"]}])


def set_user_enabled(deployment: dict, user_ref: str,
                     enabled: bool) -> OpResult:
    user = find_user(deployment, user_ref)
    if user is None:
        return OpResult(False, f"Unknown user '{user_ref}'.")
    if user["enabled"] == enabled:
        state = "enabled" if enabled else "disabled"
        return OpResult(False, f"'{user['username']}' is already {state}.")
    user["enabled"] = enabled
    if enabled:
        return OpResult(
            True, f"✔ '{user['username']}' enabled.",
            events=[{"type": "iam_user_enabled",
                     "username": user["username"]}])
    return OpResult(
        True,
        f"✔ '{user['username']}' DISABLED. Console and API sign-in now "
        f"refused.\n  Deactivate the access key too — keys keep working "
        f"on disabled\n  accounts in many real clouds.",
        events=[{"type": "iam_user_disabled",
                 "username": user["username"]}])


def deactivate_access_key(deployment: dict, user_ref: str) -> OpResult:
    user = find_user(deployment, user_ref)
    if user is None:
        return OpResult(False, f"Unknown user '{user_ref}'.")
    if not user["access_key_active"]:
        return OpResult(False, f"'{user['username']}' has no active "
                               f"access key.")
    user["access_key_active"] = False
    return OpResult(
        True,
        f"✔ Access key for '{user['username']}' deactivated — API calls "
        f"with the old key now fail.",
        events=[{"type": "iam_key_deactivated",
                 "username": user["username"]}])


# ===========================================================================
# Permission evaluation
# ===========================================================================
def _permission_matches(granted: str, requested: str) -> bool:
    g_service, g_action = granted.split(":")
    r_service, r_action = requested.split(":")
    service_ok = g_service in ("*", r_service)
    action_ok = g_action in ("*", r_action)
    return service_ok and action_ok


def simulate_permission(deployment: dict, user_ref: str,
                        permission: str) -> OpResult:
    """Evaluate '<service>:<action>' for a user and show the reasoning —
    the cloud twin of the AD lab's access checks."""
    user = find_user(deployment, user_ref)
    if user is None:
        return OpResult(False, f"Unknown user '{user_ref}'.")
    permission = (permission or "").strip().lower()
    if permission.count(":") != 1:
        return OpResult(False, "Use `simulate <user> <service:action>`, "
                               "e.g. `simulate dev-sita iam:delete-user`.")

    lines = [f"PERMISSION SIMULATION — {user['username']} → {permission}",
             "─" * 50]
    allowed_by = None
    if not user["enabled"]:
        lines.append(" ✖ DENIED — the account is disabled.")
    else:
        for role_slug in user["roles"]:
            role = deployment.get("roles", {}).get(role_slug)
            if role is None:
                continue
            for granted in role["permissions"]:
                match = _permission_matches(granted, permission)
                mark = "✔" if match else "·"
                lines.append(f" {mark} role {role_slug}: {granted}")
                if match and allowed_by is None:
                    allowed_by = role_slug
        lines.append("─" * 50)
        if allowed_by:
            lines.append(f" RESULT: ALLOWED (via role '{allowed_by}')")
        else:
            lines.append(" RESULT: DENIED — no attached role grants this.")
    allowed = bool(allowed_by) and user["enabled"]
    return OpResult(
        True, "\n".join(lines),
        events=[{"type": "permission_simulated",
                 "username": user["username"], "permission": permission,
                 "allowed": allowed, "via_role": allowed_by or ""}])


def user_events(deployment: dict, user: dict) -> list[dict[str, Any]]:
    """The inspection event for a user — flags computed once, here."""
    admin = _user_is_admin(deployment, user)
    return [{
        "type": "iam_user_inspected",
        "username": user["username"],
        "admin": admin,
        "excessive": admin and user["expected_role"] != "administrator",
        "stale_admin": admin and user["enabled"]
        and user["last_used_days"] >= 90,
        "mfa": user["mfa"],
    }]
