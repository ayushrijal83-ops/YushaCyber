"""Active Directory domain definitions (YC-031.0).

Domains are DATA, exactly like network topologies (YC-026.1). A domain
definition is a plain JSON-serialisable dict declaring the domain, its
OUs, users, groups, computers, shared folders and Group Policy Objects.
Everything is simulated — no real directory, no real Windows, no LDAP.

Two sources, one loader:

  · Built-ins — :data:`BUILTIN_DOMAINS` below (YUSHA.LOCAL ships first).
  · Admin-created — rows in ``ad_custom_domains`` (see models.py),
    authored through the admin Domain Builder and schema-validated with
    :func:`validate_domain_def` before they are ever accepted.

Every engine in this package is a pure function over a definition (or
the mutable per-session *directory* built from one) — so future
enterprise labs (privilege escalation, Kerberoasting awareness, GPO
hardening) reuse these engines without modification.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

# ---------------------------------------------------------------------------
# The flagship built-in domain — YUSHA.LOCAL
# ---------------------------------------------------------------------------
# Deliberately seeded with realistic problems for the security scenarios:
#   · kshrestha   — inactive for 210 days (find + disable + move)
#   · mrai        — locked out after a brute-force attack (reset + unlock)
#   · intern01    — an intern sitting in Domain Admins (least privilege)
#   · HR-Confidential share readable by ALL Domain Users (audit + revoke)
YUSHA_LOCAL: dict[str, Any] = {
    "key": "yusha-local",
    "name": "YUSHA.LOCAL",
    "netbios": "YUSHA",
    "description": "Primary training domain of Yusha Corp — a small company "
                   "with IT, HR and Finance departments.",
    "functional_level": "2016",

    "ous": [
        {"slug": "domain-controllers", "name": "Domain Controllers",
         "description": "Servers running Active Directory Domain Services."},
        {"slug": "servers", "name": "Servers",
         "description": "Member servers (file, application)."},
        {"slug": "workstations", "name": "Workstations",
         "description": "Employee desktop and laptop computers."},
        {"slug": "it", "name": "IT",
         "description": "IT department staff."},
        {"slug": "hr", "name": "HR",
         "description": "Human Resources staff."},
        {"slug": "finance", "name": "Finance",
         "description": "Finance department staff."},
        {"slug": "interns", "name": "Interns",
         "description": "Temporary intern accounts — least privilege applies."},
        {"slug": "service-accounts", "name": "Service Accounts",
         "description": "Non-human accounts used by services and jobs."},
        {"slug": "disabled-accounts", "name": "Disabled Accounts",
         "description": "Quarantine OU for deactivated accounts."},
    ],

    "groups": [
        {"slug": "domain-admins", "name": "Domain Admins", "builtin": True,
         "description": "Full administrative control of the domain. "
                        "Membership must be minimal."},
        {"slug": "domain-users", "name": "Domain Users", "builtin": True,
         "description": "Every user account in the domain."},
        {"slug": "help-desk", "name": "Help Desk", "builtin": False,
         "description": "First-line support: password resets and unlocks."},
        {"slug": "it-support", "name": "IT Support", "builtin": False,
         "description": "Second-line support and infrastructure work."},
        {"slug": "hr", "name": "HR", "builtin": False,
         "description": "Access to HR systems and confidential records."},
        {"slug": "finance", "name": "Finance", "builtin": False,
         "description": "Access to finance systems and reports."},
    ],

    "users": [
        {"sam": "administrator", "display": "Administrator", "ou": "it",
         "title": "Built-in Administrator", "groups": ["domain-admins", "domain-users"],
         "enabled": True, "locked": False, "last_logon_days": 0,
         "description": "Built-in domain administrator account."},
        {"sam": "skhadka", "display": "Sujal Khadka", "ou": "it",
         "title": "IT Manager", "groups": ["it-support", "help-desk", "domain-users"],
         "enabled": True, "locked": False, "last_logon_days": 0,
         "description": "Leads the IT team."},
        {"sam": "rthapa", "display": "Rojina Thapa", "ou": "it",
         "title": "Systems Administrator", "groups": ["it-support", "domain-users"],
         "enabled": True, "locked": False, "last_logon_days": 1,
         "description": "Maintains servers and workstations."},
        {"sam": "pgurung", "display": "Prakash Gurung", "ou": "it",
         "title": "Help Desk Technician", "groups": ["help-desk", "domain-users"],
         "enabled": True, "locked": False, "last_logon_days": 0,
         "description": "First-line support."},
        {"sam": "mrai", "display": "Manisha Rai", "ou": "hr",
         "title": "HR Officer", "groups": ["hr", "domain-users"],
         "enabled": True, "locked": True, "last_logon_days": 2,
         "failed_attempts": 14,
         "description": "SECURITY NOTE: account locked after repeated failed "
                        "logins from an unknown workstation."},
        {"sam": "lbasnet", "display": "Laxmi Basnet", "ou": "hr",
         "title": "HR Manager", "groups": ["hr", "domain-users"],
         "enabled": True, "locked": False, "last_logon_days": 1,
         "description": "Head of Human Resources."},
        {"sam": "dtamang", "display": "Dipesh Tamang", "ou": "finance",
         "title": "Accountant", "groups": ["finance", "domain-users"],
         "enabled": True, "locked": False, "last_logon_days": 3,
         "description": "Accounts payable and receivable."},
        {"sam": "kshrestha", "display": "Kabita Shrestha", "ou": "finance",
         "title": "Financial Analyst", "groups": ["finance", "domain-users"],
         "enabled": True, "locked": False, "last_logon_days": 210,
         "description": "On extended leave since last year."},
        {"sam": "intern01", "display": "Bikash Magar (Intern)", "ou": "interns",
         "title": "IT Intern", "groups": ["domain-users", "domain-admins"],
         "enabled": True, "locked": False, "last_logon_days": 0,
         "description": "Summer intern assisting the IT team."},
        {"sam": "svc-backup", "display": "Backup Service", "ou": "service-accounts",
         "title": "Service Account", "groups": ["domain-users"],
         "enabled": True, "locked": False, "last_logon_days": 0,
         "service_account": True,
         "description": "Runs the nightly backup job on FS-01."},
    ],

    "computers": [
        {"name": "DC-01", "ou": "domain-controllers", "os": "Windows Server 2022",
         "ip": "10.20.0.10", "is_dc": True,
         "description": "Primary domain controller for YUSHA.LOCAL."},
        {"name": "FS-01", "ou": "servers", "os": "Windows Server 2022",
         "ip": "10.20.0.20", "is_dc": False,
         "description": "File server hosting the shared folders."},
        {"name": "WS-101", "ou": "workstations", "os": "Windows 11",
         "ip": "10.20.1.101", "is_dc": False, "description": "IT workstation."},
        {"name": "WS-102", "ou": "workstations", "os": "Windows 11",
         "ip": "10.20.1.102", "is_dc": False, "description": "HR workstation."},
        {"name": "WS-103", "ou": "workstations", "os": "Windows 10",
         "ip": "10.20.1.103", "is_dc": False, "description": "Finance workstation."},
    ],

    # ACL entries: group slug -> right ("read" | "write" | "full")
    "shares": [
        {"slug": "public", "name": "Public", "server": "FS-01",
         "path": "\\\\FS-01\\Public",
         "description": "Company-wide announcements and forms.",
         "acl": [{"group": "domain-users", "right": "read"},
                 {"group": "it-support", "right": "full"}]},
        {"slug": "hr-confidential", "name": "HR-Confidential", "server": "FS-01",
         "path": "\\\\FS-01\\HR-Confidential",
         "description": "Salary reviews, disciplinary records, contracts.",
         "acl": [{"group": "hr", "right": "write"},
                 {"group": "domain-users", "right": "read"},   # ← the audit finding
                 {"group": "domain-admins", "right": "full"}]},
        {"slug": "finance-reports", "name": "Finance-Reports", "server": "FS-01",
         "path": "\\\\FS-01\\Finance-Reports",
         "description": "Monthly and quarterly financial reports.",
         "acl": [{"group": "finance", "right": "write"},
                 {"group": "it-support", "right": "read"},
                 {"group": "domain-admins", "right": "full"}]},
    ],

    "gpos": [
        {"slug": "default-domain-policy", "name": "Default Domain Policy",
         "linked_to": ["domain"], "kind": "security",
         "password_policy": {"min_length": 12, "complexity": True,
                             "max_age_days": 90, "history": 5},
         "lockout_policy": {"threshold": 5, "duration_minutes": 30,
                            "window_minutes": 15}},
        {"slug": "desktop-restrictions", "name": "Desktop Restrictions",
         "linked_to": ["interns", "workstations"], "kind": "desktop",
         "settings": {"control_panel": "denied", "cmd_prompt": "denied",
                      "usb_storage": "denied", "wallpaper": "locked"}},
        {"slug": "login-script", "name": "Login Script",
         "linked_to": ["domain"], "kind": "script",
         "script": "logon.bat",
         "settings": {"map_h_drive": "\\\\FS-01\\Home\\%username%",
                      "map_s_drive": "\\\\FS-01\\Public"}},
    ],
}

BUILTIN_DOMAINS: dict[str, dict[str, Any]] = {
    YUSHA_LOCAL["key"]: YUSHA_LOCAL,
}


# ---------------------------------------------------------------------------
# Loader — DB customs first, built-ins as fallback
# ---------------------------------------------------------------------------
def get_domain(key: str) -> Optional[dict[str, Any]]:
    """Resolve a domain definition by key.

    Admin-created domains shadow built-ins on key collision (so an admin
    can clone-and-tweak YUSHA.LOCAL under the same key if they really
    want to). Falls back cleanly when the DB is unavailable — engines
    must work in pure unit tests with no app context.
    """
    key = (key or "").strip().lower()
    try:
        from app.labs.ad.models import ADCustomDomain
        row = ADCustomDomain.query.filter_by(key=key, is_active=True).first()
        if row is not None:
            definition = row.get_definition()
            if definition:
                return definition
    except Exception:  # noqa: BLE001 — no app/db context (unit tests) is fine
        pass
    return BUILTIN_DOMAINS.get(key)


def list_domains() -> list[dict[str, Any]]:
    """Catalogue of every available domain (built-in + active customs)."""
    catalogue: dict[str, dict[str, Any]] = {}
    for key, definition in BUILTIN_DOMAINS.items():
        catalogue[key] = {"key": key, "name": definition["name"],
                          "description": definition.get("description", ""),
                          "source": "builtin"}
    try:
        from app.labs.ad.models import ADCustomDomain
        for row in ADCustomDomain.query.filter_by(is_active=True).all():
            catalogue[row.key] = {"key": row.key, "name": row.name,
                                  "description": row.description or "",
                                  "source": "custom"}
    except Exception:  # noqa: BLE001
        pass
    return sorted(catalogue.values(), key=lambda d: d["key"])


# ---------------------------------------------------------------------------
# Schema validation — the gate every admin-created domain must pass
# ---------------------------------------------------------------------------
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,63}$")
_SAM_RE = re.compile(r"^[a-z0-9][a-z0-9\-_.]{0,31}$")
_RIGHTS = {"read", "write", "full"}


def validate_domain_def(definition: Any) -> list[str]:
    """Validate a domain definition dict. Returns a list of error strings
    (empty == valid). Mirrors the topology engine's philosophy: malformed
    content fails loudly at authoring time, never at lab time."""
    errors: list[str] = []
    if not isinstance(definition, dict):
        return ["Definition must be a JSON object."]

    for field in ("key", "name"):
        if not str(definition.get(field, "")).strip():
            errors.append(f"'{field}' is required.")
    key = str(definition.get("key", "")).strip().lower()
    if key and not _SLUG_RE.match(key):
        errors.append("'key' must be a lowercase slug (a-z, 0-9, hyphen).")

    ous = definition.get("ous", [])
    groups = definition.get("groups", [])
    users = definition.get("users", [])
    computers = definition.get("computers", [])
    shares = definition.get("shares", [])
    gpos = definition.get("gpos", [])
    for name, value in (("ous", ous), ("groups", groups), ("users", users),
                        ("computers", computers), ("shares", shares),
                        ("gpos", gpos)):
        if not isinstance(value, list):
            errors.append(f"'{name}' must be a list.")
            return errors  # structure is too broken to keep checking

    ou_slugs = set()
    for i, ou in enumerate(ous):
        slug = str(ou.get("slug", "")).strip().lower()
        if not _SLUG_RE.match(slug):
            errors.append(f"ous[{i}]: invalid or missing slug.")
        elif slug in ou_slugs:
            errors.append(f"ous[{i}]: duplicate slug '{slug}'.")
        ou_slugs.add(slug)
        if not str(ou.get("name", "")).strip():
            errors.append(f"ous[{i}]: 'name' is required.")

    group_slugs = set()
    for i, group in enumerate(groups):
        slug = str(group.get("slug", "")).strip().lower()
        if not _SLUG_RE.match(slug):
            errors.append(f"groups[{i}]: invalid or missing slug.")
        elif slug in group_slugs:
            errors.append(f"groups[{i}]: duplicate slug '{slug}'.")
        group_slugs.add(slug)
        if not str(group.get("name", "")).strip():
            errors.append(f"groups[{i}]: 'name' is required.")

    sams = set()
    for i, user in enumerate(users):
        sam = str(user.get("sam", "")).strip().lower()
        if not _SAM_RE.match(sam):
            errors.append(f"users[{i}]: invalid or missing sam.")
        elif sam in sams:
            errors.append(f"users[{i}]: duplicate sam '{sam}'.")
        sams.add(sam)
        if not str(user.get("display", "")).strip():
            errors.append(f"users[{i}] ({sam}): 'display' is required.")
        ou = str(user.get("ou", "")).strip().lower()
        if ou and ou not in ou_slugs:
            errors.append(f"users[{i}] ({sam}): unknown OU '{ou}'.")
        for g in user.get("groups", []):
            if str(g).strip().lower() not in group_slugs:
                errors.append(f"users[{i}] ({sam}): unknown group '{g}'.")
        days = user.get("last_logon_days", 0)
        if not isinstance(days, int) or days < 0:
            errors.append(f"users[{i}] ({sam}): last_logon_days must be an "
                          f"integer ≥ 0.")

    computer_names = set()
    for i, comp in enumerate(computers):
        name = str(comp.get("name", "")).strip()
        if not name:
            errors.append(f"computers[{i}]: 'name' is required.")
        elif name.lower() in computer_names:
            errors.append(f"computers[{i}]: duplicate name '{name}'.")
        computer_names.add(name.lower())
        ou = str(comp.get("ou", "")).strip().lower()
        if ou and ou not in ou_slugs:
            errors.append(f"computers[{i}] ({name}): unknown OU '{ou}'.")

    share_slugs = set()
    for i, share in enumerate(shares):
        slug = str(share.get("slug", "")).strip().lower()
        if not _SLUG_RE.match(slug):
            errors.append(f"shares[{i}]: invalid or missing slug.")
        elif slug in share_slugs:
            errors.append(f"shares[{i}]: duplicate slug '{slug}'.")
        share_slugs.add(slug)
        server = str(share.get("server", "")).strip().lower()
        if server and server not in computer_names:
            errors.append(f"shares[{i}] ({slug}): unknown server '{server}'.")
        for j, entry in enumerate(share.get("acl", [])):
            if str(entry.get("group", "")).strip().lower() not in group_slugs:
                errors.append(f"shares[{i}].acl[{j}]: unknown group "
                              f"'{entry.get('group')}'.")
            if str(entry.get("right", "")).strip().lower() not in _RIGHTS:
                errors.append(f"shares[{i}].acl[{j}]: right must be one of "
                              f"{sorted(_RIGHTS)}.")

    for i, gpo in enumerate(gpos):
        slug = str(gpo.get("slug", "")).strip().lower()
        if not _SLUG_RE.match(slug):
            errors.append(f"gpos[{i}]: invalid or missing slug.")
        if not str(gpo.get("name", "")).strip():
            errors.append(f"gpos[{i}]: 'name' is required.")
        pw = gpo.get("password_policy")
        if pw is not None:
            if not isinstance(pw.get("min_length", 0), int) \
                    or pw.get("min_length", 0) < 1:
                errors.append(f"gpos[{i}]: password_policy.min_length must be "
                              f"a positive integer.")
        lock = gpo.get("lockout_policy")
        if lock is not None:
            if not isinstance(lock.get("threshold", 0), int) \
                    or lock.get("threshold", 0) < 1:
                errors.append(f"gpos[{i}]: lockout_policy.threshold must be "
                              f"a positive integer.")

    return errors


def parse_domain_json(raw: str) -> tuple[Optional[dict[str, Any]], list[str]]:
    """Parse + validate a JSON string. Returns (definition, errors)."""
    try:
        definition = json.loads(raw or "")
    except (TypeError, ValueError) as exc:
        return None, [f"Invalid JSON: {exc}"]
    errors = validate_domain_def(definition)
    return (definition if not errors else None), errors
