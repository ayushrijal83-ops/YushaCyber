"""Cloud Engine (YC-032.0) — deployment state, lookups, audit.

Turns an account definition into the mutable session "deployment",
resolves objects by slug or display name, formats compute resources,
builds the explorer tree, and runs the misconfiguration audit that the
security labs use to verify remediations.

Pure functions over plain dicts — JSON-safe, no DB, no app context.
Future provider modules (AWS/Azure/GCP flavours) reuse this unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpResult:
    """Outcome of an engine operation: console text + validator events."""
    ok: bool
    message: str
    events: list[dict[str, Any]] = field(default_factory=list)


# ===========================================================================
# Deployment build
# ===========================================================================
def build_deployment(definition: dict[str, Any]) -> dict[str, Any]:
    """Definition -> session deployment. Everything the labs mutate
    (bucket flags, roles, SG rules…) is deep-copied into plain dicts."""
    roles = {r["slug"]: {
        "slug": r["slug"], "name": r.get("name", r["slug"]),
        "description": r.get("description", ""),
        "permissions": list(r.get("permissions", [])),
    } for r in definition.get("roles", [])}

    users = {u["username"]: {
        "username": u["username"],
        "display": u.get("display", u["username"]),
        "roles": list(u.get("roles", [])),
        "expected_role": u.get("expected_role", ""),
        "mfa": bool(u.get("mfa", False)),
        "access_key_active": bool(u.get("access_key_active", False)),
        "last_used_days": int(u.get("last_used_days", 0)),
        "enabled": bool(u.get("enabled", True)),
        "description": u.get("description", ""),
    } for u in definition.get("iam_users", [])}

    buckets = {b["slug"]: {
        "slug": b["slug"], "name": b.get("name", b["slug"]),
        "public": bool(b.get("public", False)),
        "encrypted": bool(b.get("encrypted", False)),
        "versioning": bool(b.get("versioning", False)),
        "intended_public": bool(b.get("intended_public", False)),
        "description": b.get("description", ""),
        "objects": [dict(o) for o in b.get("objects", [])],
    } for b in definition.get("buckets", [])}

    vpcs = {v["slug"]: {
        "slug": v["slug"], "name": v.get("name", v["slug"]),
        "cidr": v.get("cidr", ""),
        "internet_gateway": bool(v.get("internet_gateway", False)),
        "subnets": [dict(s) for s in v.get("subnets", [])],
    } for v in definition.get("vpcs", [])}

    sgs = {g["slug"]: {
        "slug": g["slug"], "name": g.get("name", g["slug"]),
        "description": g.get("description", ""),
        "rules": [dict(r) for r in g.get("rules", [])],
    } for g in definition.get("security_groups", [])}

    vms = {m["slug"]: {
        "slug": m["slug"], "name": m.get("name", m["slug"]),
        "subnet": m.get("subnet", ""),
        "security_group": m.get("security_group", ""),
        "public_ip": m.get("public_ip"),
        "state": m.get("state", "running"),
        "size": m.get("size", "small"),
        "description": m.get("description", ""),
    } for m in definition.get("vms", [])}

    lbs = {b["slug"]: {
        "slug": b["slug"], "name": b.get("name", b["slug"]),
        "scheme": b.get("scheme", "internal"),
        "targets": list(b.get("targets", [])),
        "listener": b.get("listener", ""),
        "description": b.get("description", ""),
    } for b in definition.get("load_balancers", [])}

    dbs = {d["slug"]: {
        "slug": d["slug"], "name": d.get("name", d["slug"]),
        "engine": d.get("engine", "postgres"),
        "subnet": d.get("subnet", ""),
        "security_group": d.get("security_group", ""),
        "publicly_accessible": bool(d.get("publicly_accessible", False)),
        "encrypted": bool(d.get("encrypted", False)),
        "description": d.get("description", ""),
    } for d in definition.get("databases", [])}

    return {
        "account": {
            "key": definition.get("key", ""),
            "provider": definition.get("provider", "yushacloud"),
            "name": definition.get("name", ""),
            "account_id": definition.get("account_id", ""),
            "region": definition.get("region", ""),
            "description": definition.get("description", ""),
        },
        "roles": roles,
        "users": users,
        "buckets": buckets,
        "vpcs": vpcs,
        "security_groups": sgs,
        "vms": vms,
        "load_balancers": lbs,
        "databases": dbs,
        "password_policy": dict(definition.get("password_policy", {})),
    }


# ===========================================================================
# Lookups — by slug or display name, case-insensitive
# ===========================================================================
def _find(collection: dict[str, dict], ref: str,
          name_field: str = "name") -> dict | None:
    ref = (ref or "").strip().lower()
    if not ref:
        return None
    if ref in collection:
        return collection[ref]
    for item in collection.values():
        if item.get(name_field, "").lower() == ref:
            return item
    return None


def find_user(deployment: dict, ref: str) -> dict | None:
    ref = (ref or "").strip().lower()
    users = deployment.get("users", {})
    if ref in users:
        return users[ref]
    for user in users.values():
        if user.get("display", "").lower() == ref:
            return user
    return None


def find_role(deployment: dict, ref: str) -> dict | None:
    return _find(deployment.get("roles", {}), ref)


def find_bucket(deployment: dict, ref: str) -> dict | None:
    return _find(deployment.get("buckets", {}), ref)


def find_vpc(deployment: dict, ref: str) -> dict | None:
    return _find(deployment.get("vpcs", {}), ref)


def find_subnet(deployment: dict, ref: str) -> tuple[dict, dict] | None:
    """Returns (vpc, subnet) or None."""
    ref = (ref or "").strip().lower()
    for vpc in deployment.get("vpcs", {}).values():
        for subnet in vpc.get("subnets", []):
            if subnet.get("slug", "").lower() == ref:
                return vpc, subnet
    return None


def find_sg(deployment: dict, ref: str) -> dict | None:
    return _find(deployment.get("security_groups", {}), ref)


def find_vm(deployment: dict, ref: str) -> dict | None:
    return _find(deployment.get("vms", {}), ref)


def find_lb(deployment: dict, ref: str) -> dict | None:
    return _find(deployment.get("load_balancers", {}), ref)


def find_db(deployment: dict, ref: str) -> dict | None:
    return _find(deployment.get("databases", {}), ref)


# ===========================================================================
# Compute / LB formatting (owned by the Cloud Engine)
# ===========================================================================
def format_vm_table(deployment: dict) -> str:
    lines = [f"{'NAME':<12}{'STATE':<10}{'SUBNET':<12}{'SEC GROUP':<10}"
             f"{'PUBLIC IP':<16}SIZE"]
    lines.append("─" * 66)
    for vm in deployment.get("vms", {}).values():
        lines.append(f"{vm['name']:<12}{vm['state']:<10}{vm['subnet']:<12}"
                     f"{vm['security_group']:<10}"
                     f"{vm['public_ip'] or '—':<16}{vm['size']}")
    return "\n".join(lines)


def format_vm(deployment: dict, vm: dict) -> str:
    exposure = ("internet-reachable via public IP" if vm.get("public_ip")
                else "private — no public IP")
    return (f"VM: {vm['name']}\n"
            f"  State:          {vm['state']}\n"
            f"  Size:           {vm['size']}\n"
            f"  Subnet:         {vm['subnet']}\n"
            f"  Security group: {vm['security_group']}\n"
            f"  Public IP:      {vm['public_ip'] or '—'}  ({exposure})\n"
            f"  {vm['description']}")


def format_lb_table(deployment: dict) -> str:
    lines = [f"{'NAME':<12}{'SCHEME':<18}{'LISTENER':<12}TARGETS"]
    lines.append("─" * 60)
    for lb in deployment.get("load_balancers", {}).values():
        lines.append(f"{lb['name']:<12}{lb['scheme']:<18}"
                     f"{lb['listener']:<12}{', '.join(lb['targets'])}")
    return "\n".join(lines)


def format_overview(deployment: dict) -> str:
    account = deployment.get("account", {})
    return (
        f"╔══════════════════════════════════════════════════╗\n"
        f"║        YUSHACLOUD MANAGEMENT CONSOLE (SIM)        ║\n"
        f"╚══════════════════════════════════════════════════╝\n"
        f"\n"
        f"Account:  {account.get('name', '?')}  "
        f"({account.get('account_id', '?')})\n"
        f"Region:   {account.get('region', '?')}\n"
        f"{account.get('description', '')}\n"
        f"\n"
        f"  RESOURCES\n"
        f"  IAM users:        {len(deployment.get('users', {}))}\n"
        f"  IAM roles:        {len(deployment.get('roles', {}))}\n"
        f"  Storage buckets:  {len(deployment.get('buckets', {}))}\n"
        f"  VPCs:             {len(deployment.get('vpcs', {}))}\n"
        f"  Security groups:  {len(deployment.get('security_groups', {}))}\n"
        f"  Virtual machines: {len(deployment.get('vms', {}))}\n"
        f"  Load balancers:   {len(deployment.get('load_balancers', {}))}\n"
        f"  Databases:        {len(deployment.get('databases', {}))}\n"
        f"\n"
        f"Run `audit` for a security posture scan, `help` for commands."
    )


# ===========================================================================
# Security audit — the labs' verification backbone
# ===========================================================================
def _sg_open_to_world(sg: dict, port: int) -> bool:
    return any(r.get("direction") == "ingress" and r.get("port") == port
               and r.get("cidr") == "0.0.0.0/0"
               for r in sg.get("rules", []))


def audit_findings(deployment: dict) -> dict[str, list[str]]:
    """Current misconfigurations, grouped. Keys are stable — the seeds'
    verification objectives hang off the per-group counts."""
    findings: dict[str, list[str]] = {
        "public_buckets": [], "excessive_iam": [], "open_ssh": [],
        "public_dbs": [], "weak_policy": [], "unused_admins": [],
    }

    for bucket in deployment.get("buckets", {}).values():
        if bucket["public"] and not bucket["intended_public"]:
            findings["public_buckets"].append(
                f"bucket '{bucket['name']}' is PUBLIC but holds "
                f"non-public data")

    for user in deployment.get("users", {}).values():
        privileged = _user_is_admin(deployment, user)
        if privileged and user["expected_role"] != "administrator":
            findings["excessive_iam"].append(
                f"user '{user['username']}' holds Administrator beyond "
                f"their role")
        if (privileged and user["enabled"]
                and user["last_used_days"] >= 90):
            findings["unused_admins"].append(
                f"admin '{user['username']}' unused for "
                f"{user['last_used_days']} days")

    for sg in deployment.get("security_groups", {}).values():
        if _sg_open_to_world(sg, 22):
            findings["open_ssh"].append(
                f"security group '{sg['name']}' allows SSH (22) from "
                f"0.0.0.0/0")

    for database in deployment.get("databases", {}).values():
        sg = deployment.get("security_groups", {}).get(
            database.get("security_group", ""), {})
        exposed = database["publicly_accessible"] or \
            _sg_open_to_world(sg, 5432)
        if exposed:
            findings["public_dbs"].append(
                f"database '{database['name']}' is reachable from the "
                f"internet")

    policy = deployment.get("password_policy", {})
    if int(policy.get("min_length", 0)) < 12 or \
            not policy.get("mfa_required", False):
        findings["weak_policy"].append(
            "password policy below baseline (need min length 12 + "
            "MFA required)")

    return findings


def _user_is_admin(deployment: dict, user: dict) -> bool:
    for role_slug in user.get("roles", []):
        role = deployment.get("roles", {}).get(role_slug, {})
        if "*:*" in role.get("permissions", []):
            return True
    return False


def format_audit(deployment: dict) -> str:
    findings = audit_findings(deployment)
    total = sum(len(v) for v in findings.values())
    labels = {
        "public_buckets": "Public storage exposure",
        "excessive_iam": "Over-permissive IAM",
        "open_ssh": "SSH open to the internet",
        "public_dbs": "Databases exposed publicly",
        "weak_policy": "Weak password policy",
        "unused_admins": "Unused administrator accounts",
    }
    lines = ["SECURITY AUDIT — misconfiguration scan", "─" * 46]
    for key, label in labels.items():
        entries = findings[key]
        mark = "✔" if not entries else "✖"
        lines.append(f" {mark} {label}: "
                     f"{'clean' if not entries else str(len(entries))}")
        for entry in entries:
            lines.append(f"     · {entry}")
    lines.append("─" * 46)
    lines.append(f" {total} finding(s) open."
                 if total else " All checks clean — well done.")
    return "\n".join(lines)


# ===========================================================================
# Explorer tree — drives the console UI
# ===========================================================================
def explorer_tree(deployment: dict) -> dict[str, Any]:
    account = deployment.get("account", {})
    return {
        "account": {"name": account.get("name", ""),
                    "region": account.get("region", "")},
        "iam": {
            "users": [
                {"username": u["username"], "display": u["display"],
                 "admin": _user_is_admin(deployment, u),
                 "enabled": u["enabled"], "mfa": u["mfa"],
                 "stale": u["last_used_days"] >= 90}
                for u in deployment.get("users", {}).values()],
            "roles": [
                {"slug": r["slug"], "name": r["name"],
                 "admin": "*:*" in r["permissions"]}
                for r in deployment.get("roles", {}).values()],
        },
        "buckets": [
            {"slug": b["slug"], "name": b["name"], "public": b["public"],
             "encrypted": b["encrypted"]}
            for b in deployment.get("buckets", {}).values()],
        "network": [
            {"slug": v["slug"], "name": v["name"], "cidr": v["cidr"],
             "subnets": [{"slug": s["slug"], "cidr": s.get("cidr", ""),
                          "public": bool(s.get("public"))}
                         for s in v.get("subnets", [])]}
            for v in deployment.get("vpcs", {}).values()],
        "security_groups": [
            {"slug": g["slug"], "name": g["name"],
             "open_ssh": _sg_open_to_world(g, 22)}
            for g in deployment.get("security_groups", {}).values()],
        "vms": [
            {"slug": m["slug"], "name": m["name"], "state": m["state"],
             "public": bool(m["public_ip"])}
            for m in deployment.get("vms", {}).values()],
        "load_balancers": [
            {"slug": b["slug"], "name": b["name"], "scheme": b["scheme"]}
            for b in deployment.get("load_balancers", {}).values()],
        "databases": [
            {"slug": d["slug"], "name": d["name"],
             "public": d["publicly_accessible"] or _sg_open_to_world(
                 deployment.get("security_groups", {}).get(
                     d.get("security_group", ""), {}), 5432)}
            for d in deployment.get("databases", {}).values()],
    }
