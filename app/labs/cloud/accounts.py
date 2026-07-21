"""Cloud account definitions (YC-032.0).

Built-in scenario accounts live here as plain data; admin-authored
customs live in the DB (models.CloudCustomScenario) and shadow the
builtins by key. The definition is provider-agnostic — `provider`
is a label today ("yushacloud") and the seam where AWS/Azure/GCP
flavoured accounts plug in later without touching the engines.

Everything is simulated. Nothing here talks to a real cloud.
"""

from __future__ import annotations

import json
import re
from typing import Any

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

#: Rights understood by the IAM permission model. A permission is
#: "<service>:<action>" or a wildcard on either side.
SERVICES = ("compute", "storage", "iam", "network", "database", "billing")


YUSHACLOUD_PROD = {
    "key": "yushacloud-prod",
    "provider": "yushacloud",
    "name": "YushaCloud — Production",
    "account_id": "yc-100200300",
    "region": "np-ktm-1",
    "description": "Production account of a small SaaS company. Recent "
                   "growth outpaced its security hygiene — several classic "
                   "misconfigurations are waiting to be found.",

    # ---- IAM ----------------------------------------------------------
    "roles": [
        {"slug": "administrator", "name": "Administrator",
         "description": "Full control of every service.",
         "permissions": ["*:*"]},
        {"slug": "developer", "name": "Developer",
         "description": "Build and run application workloads.",
         "permissions": ["compute:*", "storage:read", "storage:write",
                         "database:read"]},
        {"slug": "storage-admin", "name": "Storage Admin",
         "description": "Manage buckets and objects.",
         "permissions": ["storage:*"]},
        {"slug": "auditor", "name": "Auditor",
         "description": "Read-only visibility across the account.",
         "permissions": ["compute:read", "storage:read", "iam:read",
                         "network:read", "database:read", "billing:read"]},
        {"slug": "billing-viewer", "name": "Billing Viewer",
         "description": "Read invoices and usage.",
         "permissions": ["billing:read"]},
    ],
    "iam_users": [
        {"username": "root-admin", "display": "Account Owner",
         "roles": ["administrator"], "expected_role": "administrator",
         "mfa": True, "access_key_active": True, "last_used_days": 1,
         "description": "Break-glass account owner. MFA enforced."},
        {"username": "anita-ops", "display": "Anita Gurung (Ops)",
         "roles": ["developer"], "expected_role": "developer",
         "mfa": True, "access_key_active": True, "last_used_days": 0,
         "description": "Operations engineer — deploys and monitors."},
        {"username": "dev-sita", "display": "Sita Maharjan (Developer)",
         "roles": ["developer", "administrator"], "expected_role": "developer",
         "mfa": False, "access_key_active": True, "last_used_days": 2,
         "description": "Frontend developer. Was granted Administrator "
                        "\"temporarily\" during an outage in March."},
        {"username": "bibek-dev", "display": "Bibek Thapa (Developer)",
         "roles": ["developer"], "expected_role": "developer",
         "mfa": True, "access_key_active": True, "last_used_days": 1,
         "description": "Backend developer."},
        {"username": "finance-app", "display": "Finance Service Account",
         "roles": ["billing-viewer"], "expected_role": "billing-viewer",
         "mfa": False, "access_key_active": True, "last_used_days": 3,
         "description": "Automation account for invoice exports."},
        {"username": "old-admin", "display": "Prakash Karki (departed)",
         "roles": ["administrator"], "expected_role": "administrator",
         "mfa": False, "access_key_active": True, "last_used_days": 300,
         "description": "Former sysadmin who left the company last year. "
                        "Account and access key were never off-boarded."},
        {"username": "audit-suresh", "display": "Suresh Lama (Auditor)",
         "roles": ["auditor"], "expected_role": "auditor",
         "mfa": True, "access_key_active": False, "last_used_days": 12,
         "description": "External compliance auditor (read-only)."},
    ],
    "password_policy": {
        "min_length": 6,
        "require_numbers": False,
        "require_symbols": False,
        "mfa_required": False,
        "max_age_days": 0,
    },

    # ---- Storage ------------------------------------------------------
    "buckets": [
        {"slug": "web-assets", "name": "web-assets",
         "public": True, "encrypted": True, "versioning": False,
         "intended_public": True,
         "description": "Static website images and CSS — meant to be public.",
         "objects": [
             {"key": "logo.png", "size": "48 KB", "sensitive": False},
             {"key": "style.css", "size": "12 KB", "sensitive": False},
         ]},
        {"slug": "customer-backups", "name": "customer-backups",
         "public": True, "encrypted": False, "versioning": False,
         "intended_public": False,
         "description": "Nightly database dumps. Was flipped public during "
                        "a rushed vendor file-transfer and never reverted.",
         "objects": [
             {"key": "customers-2026-07-19.sql", "size": "220 MB",
              "sensitive": True},
             {"key": "customers-2026-07-20.sql", "size": "221 MB",
              "sensitive": True},
             {"key": "payment-export.csv", "size": "4 MB", "sensitive": True},
         ]},
        {"slug": "app-releases", "name": "app-releases",
         "public": False, "encrypted": True, "versioning": True,
         "intended_public": False,
         "description": "Signed build artifacts. Versioning protects "
                        "against overwrite and ransomware.",
         "objects": [
             {"key": "app-v3.2.1.tar.gz", "size": "84 MB",
              "sensitive": False},
         ]},
    ],

    # ---- Network ------------------------------------------------------
    "vpcs": [
        {"slug": "prod-vpc", "name": "prod-vpc", "cidr": "10.50.0.0/16",
         "subnets": [
             {"slug": "public-a", "cidr": "10.50.1.0/24", "public": True,
              "description": "Internet-facing tier behind the gateway."},
             {"slug": "private-a", "cidr": "10.50.10.0/24", "public": False,
              "description": "Application tier — no internet route."},
             {"slug": "data-a", "cidr": "10.50.20.0/24", "public": False,
              "description": "Database tier — private by design."},
         ],
         "internet_gateway": True},
    ],
    "security_groups": [
        {"slug": "web-sg", "name": "web-sg",
         "description": "Web server group.",
         "rules": [
             {"direction": "ingress", "protocol": "tcp", "port": 443,
              "cidr": "0.0.0.0/0", "description": "HTTPS from anywhere"},
             {"direction": "ingress", "protocol": "tcp", "port": 80,
              "cidr": "0.0.0.0/0", "description": "HTTP from anywhere"},
             {"direction": "ingress", "protocol": "tcp", "port": 22,
              "cidr": "0.0.0.0/0",
              "description": "SSH — opened for \"quick debugging\""},
         ]},
        {"slug": "app-sg", "name": "app-sg",
         "description": "Application tier group.",
         "rules": [
             {"direction": "ingress", "protocol": "tcp", "port": 8080,
              "cidr": "10.50.1.0/24", "description": "From web tier only"},
             {"direction": "ingress", "protocol": "tcp", "port": 22,
              "cidr": "10.50.0.0/16", "description": "SSH from inside VPC"},
         ]},
        {"slug": "db-sg", "name": "db-sg",
         "description": "Database group.",
         "rules": [
             {"direction": "ingress", "protocol": "tcp", "port": 5432,
              "cidr": "0.0.0.0/0",
              "description": "PostgreSQL — vendor demo, never removed"},
         ]},
    ],

    # ---- Compute ------------------------------------------------------
    "vms": [
        {"slug": "web-01", "name": "web-01", "subnet": "public-a",
         "security_group": "web-sg", "public_ip": "203.0.113.10",
         "state": "running", "size": "small",
         "description": "Nginx front end."},
        {"slug": "web-02", "name": "web-02", "subnet": "public-a",
         "security_group": "web-sg", "public_ip": "203.0.113.11",
         "state": "running", "size": "small",
         "description": "Nginx front end (second AZ)."},
        {"slug": "app-01", "name": "app-01", "subnet": "private-a",
         "security_group": "app-sg", "public_ip": None,
         "state": "running", "size": "medium",
         "description": "Application server."},
    ],
    "load_balancers": [
        {"slug": "prod-lb", "name": "prod-lb", "scheme": "internet-facing",
         "targets": ["web-01", "web-02"], "listener": "https:443",
         "description": "Public entry point for the product."},
    ],

    # ---- Databases ----------------------------------------------------
    "databases": [
        {"slug": "customers-db", "name": "customers-db", "engine": "postgres",
         "subnet": "data-a", "security_group": "db-sg",
         "publicly_accessible": True, "encrypted": True,
         "description": "Primary customer database. Public endpoint was "
                        "enabled for a vendor demo and forgotten."},
        {"slug": "analytics-db", "name": "analytics-db", "engine": "postgres",
         "subnet": "data-a", "security_group": "app-sg",
         "publicly_accessible": False, "encrypted": True,
         "description": "Internal analytics replica."},
    ],
}

BUILTIN_ACCOUNTS: dict[str, dict[str, Any]] = {
    YUSHACLOUD_PROD["key"]: YUSHACLOUD_PROD,
}


# ===========================================================================
# Lookup — customs (DB) shadow builtins
# ===========================================================================
def get_account(key: str) -> dict[str, Any] | None:
    """Resolve an account definition by key. Admin-created scenarios in
    the DB take precedence; failures (no app context, missing table)
    fall back silently to the builtins."""
    key = (key or "").strip().lower()
    try:
        from app.labs.cloud.models import CloudCustomScenario
        row = CloudCustomScenario.query.filter_by(
            key=key, is_active=True).first()
        if row is not None:
            definition = row.get_definition()
            if definition:
                return definition
    except Exception:  # pragma: no cover — outside app context
        pass
    return BUILTIN_ACCOUNTS.get(key)


def list_accounts() -> list[dict[str, Any]]:
    """Builtins plus active customs (customs shadow same-key builtins)."""
    merged: dict[str, dict[str, Any]] = dict(BUILTIN_ACCOUNTS)
    try:
        from app.labs.cloud.models import CloudCustomScenario
        for row in CloudCustomScenario.query.filter_by(is_active=True).all():
            definition = row.get_definition()
            if definition.get("key"):
                merged[definition["key"]] = definition
    except Exception:  # pragma: no cover
        pass
    return list(merged.values())


# ===========================================================================
# Validation — the admin Scenario Builder's contract
# ===========================================================================
def _check_slug(value: Any, where: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not _SLUG_RE.match(value):
        errors.append(f"{where}: '{value}' is not a lowercase slug "
                      f"(a-z, 0-9, hyphens).")


def _dupes(items: list[dict], field: str, where: str,
           errors: list[str]) -> None:
    seen: set[str] = set()
    for item in items:
        value = item.get(field, "")
        if value in seen:
            errors.append(f"{where}: duplicate slug '{value}'.")
        seen.add(value)


def _permission_ok(perm: str) -> bool:
    if not isinstance(perm, str) or perm.count(":") != 1:
        return False
    service, action = perm.split(":")
    return (service == "*" or service in SERVICES) and bool(action)


def validate_account_def(definition: dict[str, Any]) -> list[str]:
    """Return a list of human-readable problems; empty list = valid."""
    errors: list[str] = []
    if not isinstance(definition, dict):
        return ["Definition must be a JSON object."]

    _check_slug(definition.get("key"), "account key", errors)
    if not definition.get("name"):
        errors.append("account: 'name' is required.")

    roles = definition.get("roles", [])
    users = definition.get("iam_users", [])
    buckets = definition.get("buckets", [])
    vpcs = definition.get("vpcs", [])
    sgs = definition.get("security_groups", [])
    vms = definition.get("vms", [])
    lbs = definition.get("load_balancers", [])
    dbs = definition.get("databases", [])
    for name, seq in (("roles", roles), ("iam_users", users),
                      ("buckets", buckets), ("vpcs", vpcs),
                      ("security_groups", sgs), ("vms", vms),
                      ("load_balancers", lbs), ("databases", dbs)):
        if not isinstance(seq, list):
            errors.append(f"{name}: must be a list.")
            return errors

    role_slugs = set()
    for role in roles:
        _check_slug(role.get("slug"), "role", errors)
        role_slugs.add(role.get("slug"))
        for perm in role.get("permissions", []):
            if not _permission_ok(perm):
                errors.append(
                    f"role '{role.get('slug')}': bad permission '{perm}' "
                    f"(expected service:action, services: "
                    f"{', '.join(SERVICES)} or *).")
    _dupes(roles, "slug", "roles", errors)

    usernames = set()
    for user in users:
        _check_slug(user.get("username"), "iam user", errors)
        usernames.add(user.get("username"))
        for role in user.get("roles", []):
            if role not in role_slugs:
                errors.append(f"iam user '{user.get('username')}': "
                              f"unknown role '{role}'.")
    _dupes(users, "username", "iam_users", errors)

    subnet_slugs = set()
    for vpc in vpcs:
        _check_slug(vpc.get("slug"), "vpc", errors)
        for subnet in vpc.get("subnets", []):
            _check_slug(subnet.get("slug"), "subnet", errors)
            subnet_slugs.add(subnet.get("slug"))

    sg_slugs = set()
    for sg in sgs:
        _check_slug(sg.get("slug"), "security group", errors)
        sg_slugs.add(sg.get("slug"))
        for rule in sg.get("rules", []):
            if rule.get("direction") not in ("ingress", "egress"):
                errors.append(f"security group '{sg.get('slug')}': rule "
                              f"direction must be ingress or egress.")
            if not isinstance(rule.get("port"), int):
                errors.append(f"security group '{sg.get('slug')}': rule "
                              f"port must be an integer.")
    _dupes(sgs, "slug", "security_groups", errors)

    _dupes(buckets, "slug", "buckets", errors)
    for bucket in buckets:
        _check_slug(bucket.get("slug"), "bucket", errors)

    for vm in vms:
        _check_slug(vm.get("slug"), "vm", errors)
        if vm.get("subnet") not in subnet_slugs:
            errors.append(f"vm '{vm.get('slug')}': unknown subnet "
                          f"'{vm.get('subnet')}'.")
        if vm.get("security_group") not in sg_slugs:
            errors.append(f"vm '{vm.get('slug')}': unknown security group "
                          f"'{vm.get('security_group')}'.")
    _dupes(vms, "slug", "vms", errors)

    for lb in lbs:
        _check_slug(lb.get("slug"), "load balancer", errors)
        vm_slugs = {vm.get("slug") for vm in vms}
        for target in lb.get("targets", []):
            if target not in vm_slugs:
                errors.append(f"load balancer '{lb.get('slug')}': unknown "
                              f"target '{target}'.")

    for database in dbs:
        _check_slug(database.get("slug"), "database", errors)
        if database.get("subnet") not in subnet_slugs:
            errors.append(f"database '{database.get('slug')}': unknown "
                          f"subnet '{database.get('subnet')}'.")
        if database.get("security_group") not in sg_slugs:
            errors.append(f"database '{database.get('slug')}': unknown "
                          f"security group '{database.get('security_group')}'.")
    _dupes(dbs, "slug", "databases", errors)

    return errors


def parse_account_json(raw: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse + validate admin JSON. Returns (definition, errors)."""
    try:
        definition = json.loads(raw or "")
    except ValueError as exc:
        return None, [f"Invalid JSON: {exc}"]
    errors = validate_account_def(definition)
    return (definition if not errors else None), errors
