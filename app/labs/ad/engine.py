"""Domain Engine (YC-031.0) — build + query the simulated directory.

A *definition* (domains.py) is immutable authoring data. A *directory*
is the mutable per-session copy the student operates on, stored inside
the lab session state envelope exactly like every other simulator's
state. Building it here — one canonical shape — is what lets the User,
Group, Policy and Permission engines stay pure and reusable.

Directory shape (all JSON-serialisable):

    {
      "domain":    {key, name, netbios, description, functional_level},
      "ous":       {slug: {slug, name, description}},
      "groups":    {slug: {slug, name, description, builtin, members: [sam]}},
      "users":     {sam:  {sam, display, title, ou, groups: [slug], enabled,
                           locked, failed_attempts, last_logon_days,
                           service_account, description, password_set: bool}},
      "computers": {name_lower: {name, ou, os, ip, is_dc, description}},
      "shares":    {slug: {slug, name, server, path, description,
                           acl: [{group, right}]}},
      "gpos":      {slug: {...verbatim from the definition...}},
    }
"""

from __future__ import annotations

from typing import Any, Optional


def build_directory(definition: dict[str, Any]) -> dict[str, Any]:
    """Materialise a mutable directory from an immutable definition."""
    directory: dict[str, Any] = {
        "domain": {
            "key": definition.get("key", ""),
            "name": definition.get("name", ""),
            "netbios": definition.get("netbios", ""),
            "description": definition.get("description", ""),
            "functional_level": definition.get("functional_level", "2016"),
        },
        "ous": {}, "groups": {}, "users": {},
        "computers": {}, "shares": {}, "gpos": {},
    }

    for ou in definition.get("ous", []):
        slug = str(ou.get("slug", "")).lower()
        directory["ous"][slug] = {
            "slug": slug, "name": ou.get("name", slug),
            "description": ou.get("description", ""),
        }

    for group in definition.get("groups", []):
        slug = str(group.get("slug", "")).lower()
        directory["groups"][slug] = {
            "slug": slug, "name": group.get("name", slug),
            "description": group.get("description", ""),
            "builtin": bool(group.get("builtin", False)),
            "members": [],
        }

    for user in definition.get("users", []):
        sam = str(user.get("sam", "")).lower()
        member_of = [str(g).lower() for g in user.get("groups", [])
                     if str(g).lower() in directory["groups"]]
        directory["users"][sam] = {
            "sam": sam,
            "display": user.get("display", sam),
            "title": user.get("title", ""),
            "ou": str(user.get("ou", "")).lower(),
            "groups": member_of,
            "enabled": bool(user.get("enabled", True)),
            "locked": bool(user.get("locked", False)),
            "failed_attempts": int(user.get("failed_attempts", 0)),
            "last_logon_days": int(user.get("last_logon_days", 0)),
            "service_account": bool(user.get("service_account", False)),
            "description": user.get("description", ""),
            "password_set": True,
        }
        for slug in member_of:
            directory["groups"][slug]["members"].append(sam)

    for comp in definition.get("computers", []):
        name = str(comp.get("name", ""))
        directory["computers"][name.lower()] = {
            "name": name, "ou": str(comp.get("ou", "")).lower(),
            "os": comp.get("os", ""), "ip": comp.get("ip", ""),
            "is_dc": bool(comp.get("is_dc", False)),
            "description": comp.get("description", ""),
        }

    for share in definition.get("shares", []):
        slug = str(share.get("slug", "")).lower()
        directory["shares"][slug] = {
            "slug": slug, "name": share.get("name", slug),
            "server": share.get("server", ""),
            "path": share.get("path", ""),
            "description": share.get("description", ""),
            "acl": [{"group": str(e.get("group", "")).lower(),
                     "right": str(e.get("right", "read")).lower()}
                    for e in share.get("acl", [])],
        }

    for gpo in definition.get("gpos", []):
        slug = str(gpo.get("slug", "")).lower()
        directory["gpos"][slug] = dict(gpo, slug=slug)

    return directory


# ---------------------------------------------------------------------------
# Lookups — every engine and every command resolves objects through these,
# so name handling (case, quotes, display names vs slugs) is defined once.
# ---------------------------------------------------------------------------
def find_user(directory: dict[str, Any], key: str) -> Optional[dict[str, Any]]:
    """Match a user by sAMAccountName or display name (case-insensitive)."""
    key = (key or "").strip().lower()
    if not key:
        return None
    user = directory.get("users", {}).get(key)
    if user is not None:
        return user
    for candidate in directory.get("users", {}).values():
        if candidate.get("display", "").lower() == key:
            return candidate
    return None


def find_group(directory: dict[str, Any], key: str) -> Optional[dict[str, Any]]:
    """Match a group by slug or display name (case-insensitive)."""
    key = (key or "").strip().lower()
    if not key:
        return None
    group = directory.get("groups", {}).get(key)
    if group is not None:
        return group
    for candidate in directory.get("groups", {}).values():
        if candidate.get("name", "").lower() == key:
            return candidate
    return None


def find_ou(directory: dict[str, Any], key: str) -> Optional[dict[str, Any]]:
    key = (key or "").strip().lower()
    if not key:
        return None
    ou = directory.get("ous", {}).get(key)
    if ou is not None:
        return ou
    for candidate in directory.get("ous", {}).values():
        if candidate.get("name", "").lower() == key:
            return candidate
    return None


def find_computer(directory: dict[str, Any], key: str) -> Optional[dict[str, Any]]:
    key = (key or "").strip().lower()
    return directory.get("computers", {}).get(key) if key else None


def find_share(directory: dict[str, Any], key: str) -> Optional[dict[str, Any]]:
    key = (key or "").strip().lower()
    if not key:
        return None
    share = directory.get("shares", {}).get(key)
    if share is not None:
        return share
    for candidate in directory.get("shares", {}).values():
        if candidate.get("name", "").lower() == key:
            return candidate
    return None


def find_gpo(directory: dict[str, Any], key: str) -> Optional[dict[str, Any]]:
    key = (key or "").strip().lower()
    if not key:
        return None
    gpo = directory.get("gpos", {}).get(key)
    if gpo is not None:
        return gpo
    for candidate in directory.get("gpos", {}).values():
        if candidate.get("name", "").lower() == key:
            return candidate
    return None


def users_in_ou(directory: dict[str, Any], ou_slug: str) -> list[dict[str, Any]]:
    ou_slug = (ou_slug or "").lower()
    return sorted(
        (u for u in directory.get("users", {}).values()
         if u.get("ou") == ou_slug),
        key=lambda u: u["sam"],
    )


def computers_in_ou(directory: dict[str, Any], ou_slug: str) -> list[dict[str, Any]]:
    ou_slug = (ou_slug or "").lower()
    return sorted(
        (c for c in directory.get("computers", {}).values()
         if c.get("ou") == ou_slug),
        key=lambda c: c["name"],
    )


# ---------------------------------------------------------------------------
# Explorer tree — the payload the frontend tree navigation renders.
# ---------------------------------------------------------------------------
def explorer_tree(directory: dict[str, Any]) -> dict[str, Any]:
    """The full object tree for the UI: domain → OUs → users/computers,
    plus flat groups and shares sections. JSON-ready, no secrets."""
    ous = []
    for slug in sorted(directory.get("ous", {})):
        ou = directory["ous"][slug]
        ous.append({
            "slug": slug,
            "name": ou["name"],
            "users": [
                {"sam": u["sam"], "display": u["display"],
                 "enabled": u["enabled"], "locked": u["locked"]}
                for u in users_in_ou(directory, slug)
            ],
            "computers": [
                {"name": c["name"], "is_dc": c["is_dc"]}
                for c in computers_in_ou(directory, slug)
            ],
        })
    return {
        "domain": directory.get("domain", {}),
        "ous": ous,
        "groups": [
            {"slug": g["slug"], "name": g["name"],
             "member_count": len(g["members"]), "builtin": g["builtin"]}
            for g in sorted(directory.get("groups", {}).values(),
                            key=lambda g: g["slug"])
        ],
        "shares": [
            {"slug": s["slug"], "name": s["name"], "server": s["server"]}
            for s in sorted(directory.get("shares", {}).values(),
                            key=lambda s: s["slug"])
        ],
        "gpos": [
            {"slug": g["slug"], "name": g["name"], "kind": g.get("kind", "")}
            for g in sorted(directory.get("gpos", {}).values(),
                            key=lambda g: g["slug"])
        ],
    }
