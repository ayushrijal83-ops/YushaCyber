"""Networking Engine (YC-032.0) — VPCs, subnets, security groups, DB exposure.

Firewall semantics are deliberately simple (ingress rules matched on
protocol/port/CIDR) — enough to teach the concepts without recreating
a real SDN. The `db_secured` event fires only when a database is
neither flagged public nor reachable through a world-open SG rule.
"""

from __future__ import annotations

from typing import Any

from app.labs.cloud.engine import OpResult, _sg_open_to_world, find_db, \
    find_sg


# ===========================================================================
# Formatting
# ===========================================================================
def format_network(deployment: dict) -> str:
    lines = ["VIRTUAL NETWORKS", "─" * 56]
    for vpc in deployment.get("vpcs", {}).values():
        gateway = ("internet gateway ATTACHED"
                   if vpc["internet_gateway"] else "no internet gateway")
        lines.append(f"VPC {vpc['name']}  {vpc['cidr']}  ({gateway})")
        for subnet in vpc["subnets"]:
            kind = "public " if subnet.get("public") else "private"
            lines.append(f"   └─ {subnet['slug']:<12}{subnet['cidr']:<16}"
                         f"{kind}  {subnet.get('description', '')}")
    return "\n".join(lines)


def format_sg_table(deployment: dict) -> str:
    lines = [f"{'GROUP':<10}{'RULES':<7}NOTE"]
    lines.append("─" * 50)
    for sg in deployment.get("security_groups", {}).values():
        note = "⚠ SSH open to 0.0.0.0/0" if _sg_open_to_world(sg, 22) else ""
        lines.append(f"{sg['name']:<10}{len(sg['rules']):<7}{note}")
    return "\n".join(lines)


def format_sg(sg: dict) -> str:
    lines = [f"SECURITY GROUP: {sg['name']}", f"  {sg['description']}",
             f"  {'DIR':<9}{'PROTO':<7}{'PORT':<7}{'SOURCE':<16}DESCRIPTION",
             "  " + "─" * 56]
    for rule in sg["rules"]:
        mark = ""
        if rule.get("direction") == "ingress" and \
                rule.get("cidr") == "0.0.0.0/0" and rule.get("port") == 22:
            mark = "  ⚠ world-open SSH"
        lines.append(f"  {rule['direction']:<9}{rule['protocol']:<7}"
                     f"{rule['port']:<7}{rule['cidr']:<16}"
                     f"{rule.get('description', '')}{mark}")
    if _sg_open_to_world(sg, 22):
        lines.append("  ⚠ FINDING: SSH (22) reachable from the entire "
                     "internet — brute-force magnet.")
    return "\n".join(lines)


def format_db_table(deployment: dict) -> str:
    lines = [f"{'DATABASE':<16}{'ENGINE':<10}{'SUBNET':<10}"
             f"{'ENCRYPTED':<11}EXPOSURE"]
    lines.append("─" * 62)
    for database in deployment.get("databases", {}).values():
        sg = deployment.get("security_groups", {}).get(
            database.get("security_group", ""), {})
        exposed = database["publicly_accessible"] or \
            _sg_open_to_world(sg, 5432)
        lines.append(
            f"{database['name']:<16}{database['engine']:<10}"
            f"{database['subnet']:<10}"
            f"{'yes' if database['encrypted'] else 'NO':<11}"
            f"{'⚠ INTERNET-REACHABLE' if exposed else 'private'}")
    return "\n".join(lines)


def format_db(deployment: dict, database: dict) -> str:
    sg = deployment.get("security_groups", {}).get(
        database.get("security_group", ""), {})
    world_rule = _sg_open_to_world(sg, 5432)
    exposed = database["publicly_accessible"] or world_rule
    lines = [
        f"DATABASE: {database['name']}  ({database['engine']})",
        f"  Subnet:            {database['subnet']}",
        f"  Security group:    {database['security_group']}",
        f"  Public endpoint:   "
        f"{'ENABLED' if database['publicly_accessible'] else 'disabled'}",
        f"  Encrypted at rest: "
        f"{'yes' if database['encrypted'] else 'NO'}",
        f"  {database['description']}",
    ]
    if exposed:
        lines.append("  ⚠ FINDING: this database is reachable from the "
                     "internet.")
        if database["publicly_accessible"]:
            lines.append("     · the public endpoint is enabled "
                         "(`make-db-private` fixes this)")
        if world_rule:
            lines.append(f"     · '{sg.get('name', '?')}' allows 5432 from "
                         f"0.0.0.0/0 (`revoke-ingress` fixes this)")
    return "\n".join(lines)


# ===========================================================================
# Operations
# ===========================================================================
def _db_secured_events(deployment: dict) -> list[dict[str, Any]]:
    """Emit db_secured per database that is fully private now."""
    events = []
    for database in deployment.get("databases", {}).values():
        sg = deployment.get("security_groups", {}).get(
            database.get("security_group", ""), {})
        if not database["publicly_accessible"] and \
                not _sg_open_to_world(sg, 5432):
            events.append({"type": "db_secured", "db": database["slug"]})
    return events


def revoke_ingress(deployment: dict, sg_ref: str, port: int,
                   cidr: str = "0.0.0.0/0") -> OpResult:
    sg = find_sg(deployment, sg_ref)
    if sg is None:
        return OpResult(False, f"Unknown security group '{sg_ref}'.")
    before = len(sg["rules"])
    sg["rules"] = [r for r in sg["rules"]
                   if not (r.get("direction") == "ingress"
                           and r.get("port") == port
                           and r.get("cidr") == cidr)]
    if len(sg["rules"]) == before:
        return OpResult(False, f"No ingress rule for port {port} from "
                               f"{cidr} on '{sg['name']}'.")
    events: list[dict[str, Any]] = [
        {"type": "sg_rule_revoked", "sg": sg["slug"], "port": port,
         "cidr": cidr}]
    if port == 5432:
        events.extend(_db_secured_events(deployment))
    return OpResult(
        True,
        f"✔ Revoked ingress {port} from {cidr} on '{sg['name']}'.\n"
        f"  Connections from that range are now dropped.",
        events=events)


def allow_ingress(deployment: dict, sg_ref: str, port: int,
                  cidr: str) -> OpResult:
    sg = find_sg(deployment, sg_ref)
    if sg is None:
        return OpResult(False, f"Unknown security group '{sg_ref}'.")
    if any(r.get("direction") == "ingress" and r.get("port") == port
           and r.get("cidr") == cidr for r in sg["rules"]):
        return OpResult(False, "That exact rule already exists.")
    sg["rules"].append({"direction": "ingress", "protocol": "tcp",
                        "port": port, "cidr": cidr,
                        "description": "added in this session"})
    warning = ("\n  ⚠ 0.0.0.0/0 means THE ENTIRE INTERNET — prefer your "
               "office or VPN range." if cidr == "0.0.0.0/0" else "")
    return OpResult(
        True,
        f"✔ Allowed ingress {port} from {cidr} on '{sg['name']}'."
        f"{warning}",
        events=[{"type": "sg_rule_added", "sg": sg["slug"], "port": port,
                 "cidr": cidr, "world_open": cidr == "0.0.0.0/0"}])


def set_db_public(deployment: dict, ref: str, public: bool) -> OpResult:
    database = find_db(deployment, ref)
    if database is None:
        return OpResult(False, f"Unknown database '{ref}'.")
    if database["publicly_accessible"] == public:
        state = "public" if public else "private"
        return OpResult(False, f"'{database['name']}' endpoint is already "
                               f"{state}.")
    database["publicly_accessible"] = public
    if public:
        return OpResult(
            True,
            f"⚠ '{database['name']}' now has a PUBLIC endpoint.",
            events=[{"type": "db_access_set", "db": database["slug"],
                     "public": True}])
    events: list[dict[str, Any]] = [
        {"type": "db_access_set", "db": database["slug"], "public": False}]
    events.extend(e for e in _db_secured_events(deployment)
                  if e["db"] == database["slug"])
    sg = deployment.get("security_groups", {}).get(
        database.get("security_group", ""), {})
    reminder = ""
    if _sg_open_to_world(sg, 5432):
        reminder = (f"\n  ⚠ '{sg.get('name', '?')}' still allows 5432 from "
                    f"0.0.0.0/0 — revoke that rule too.")
    return OpResult(
        True,
        f"✔ Public endpoint disabled on '{database['name']}' — only the "
        f"VPC can reach it now.{reminder}",
        events=events)


def sg_events(sg: dict) -> list[dict[str, Any]]:
    return [{"type": "sg_inspected", "sg": sg["slug"],
             "open_ssh": _sg_open_to_world(sg, 22),
             "rule_count": len(sg["rules"])}]


def db_events(deployment: dict, database: dict) -> list[dict[str, Any]]:
    sg = deployment.get("security_groups", {}).get(
        database.get("security_group", ""), {})
    return [{"type": "db_inspected", "db": database["slug"],
             "exposed": database["publicly_accessible"]
             or _sg_open_to_world(sg, 5432)}]
