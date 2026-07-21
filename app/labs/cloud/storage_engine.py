"""Storage Engine (YC-032.0) — buckets, access, encryption, versioning.

The `bucket_secured` event fires only on INSPECTION of a
should-be-private bucket that is now private AND encrypted — so the
verification objective demands a genuine re-check after remediation,
and never triggers on the mutation itself.
"""

from __future__ import annotations

from typing import Any

from app.labs.cloud.engine import OpResult, find_bucket


# ===========================================================================
# Formatting
# ===========================================================================
def format_bucket_table(deployment: dict) -> str:
    lines = [f"{'BUCKET':<20}{'ACCESS':<10}{'ENCRYPTION':<12}"
             f"{'VERSIONING':<12}NOTE"]
    lines.append("─" * 70)
    for bucket in deployment.get("buckets", {}).values():
        note = ""
        if bucket["public"] and not bucket["intended_public"]:
            note = "⚠ should be private"
        elif bucket["public"]:
            note = "public by design"
        lines.append(
            f"{bucket['name']:<20}"
            f"{'PUBLIC' if bucket['public'] else 'private':<10}"
            f"{'on' if bucket['encrypted'] else 'OFF':<12}"
            f"{'on' if bucket['versioning'] else 'off':<12}{note}")
    return "\n".join(lines)


def format_bucket(bucket: dict) -> str:
    policy = ("ALLOW anonymous read (public)"
              if bucket["public"] else "DENY anonymous access (private)")
    lines = [
        f"BUCKET: {bucket['name']}",
        f"  Access policy: {policy}",
        f"  Encryption:    "
        f"{'at-rest encryption ON' if bucket['encrypted'] else 'NOT encrypted'}",
        f"  Versioning:    "
        f"{'enabled' if bucket['versioning'] else 'disabled'}",
        f"  Objects:       {len(bucket['objects'])}",
        f"  {bucket['description']}",
    ]
    if bucket["public"] and not bucket["intended_public"]:
        lines.append("  ⚠ FINDING: public bucket holding non-public data — "
                     "anyone on the internet can download these objects.")
    if not bucket["encrypted"]:
        lines.append("  ⚠ Objects are stored unencrypted at rest.")
    return "\n".join(lines)


def format_objects(bucket: dict) -> str:
    lines = [f"OBJECTS IN {bucket['name']} "
             f"({'PUBLIC' if bucket['public'] else 'private'})", "─" * 50]
    sensitive = 0
    for obj in bucket["objects"]:
        mark = "⚠" if obj.get("sensitive") else " "
        if obj.get("sensitive"):
            sensitive += 1
        lines.append(f" {mark} {obj['key']:<32}{obj.get('size', '')}")
    if sensitive and bucket["public"]:
        lines.append("─" * 50)
        lines.append(f" ⚠ {sensitive} sensitive object(s) exposed to the "
                     f"internet right now.")
    return "\n".join(lines)


# ===========================================================================
# Operations
# ===========================================================================
def set_public(deployment: dict, ref: str, public: bool) -> OpResult:
    bucket = find_bucket(deployment, ref)
    if bucket is None:
        return OpResult(False, f"Unknown bucket '{ref}'.")
    if bucket["public"] == public:
        state = "public" if public else "private"
        return OpResult(False, f"'{bucket['name']}' is already {state}.")
    bucket["public"] = public
    if public:
        return OpResult(
            True,
            f"⚠ '{bucket['name']}' is now PUBLIC — anyone on the internet "
            f"can read its objects.\n  Only do this for content that is "
            f"truly public.",
            events=[{"type": "bucket_access_set", "bucket": bucket["slug"],
                     "public": True}])
    return OpResult(
        True,
        f"✔ '{bucket['name']}' is now PRIVATE. Anonymous requests get "
        f"403 Forbidden.\n  Verify with `get-bucket {bucket['slug']}`.",
        events=[{"type": "bucket_access_set", "bucket": bucket["slug"],
                 "public": False}])


def enable_encryption(deployment: dict, ref: str) -> OpResult:
    bucket = find_bucket(deployment, ref)
    if bucket is None:
        return OpResult(False, f"Unknown bucket '{ref}'.")
    if bucket["encrypted"]:
        return OpResult(False, f"'{bucket['name']}' already has encryption "
                               f"enabled.")
    bucket["encrypted"] = True
    return OpResult(
        True,
        f"✔ At-rest encryption enabled on '{bucket['name']}'. New and "
        f"existing objects are\n  encrypted with the account key.",
        events=[{"type": "bucket_encryption_enabled",
                 "bucket": bucket["slug"]}])


def enable_versioning(deployment: dict, ref: str) -> OpResult:
    bucket = find_bucket(deployment, ref)
    if bucket is None:
        return OpResult(False, f"Unknown bucket '{ref}'.")
    if bucket["versioning"]:
        return OpResult(False, f"Versioning is already on for "
                               f"'{bucket['name']}'.")
    bucket["versioning"] = True
    return OpResult(
        True,
        f"✔ Versioning enabled on '{bucket['name']}' — overwrites and "
        f"deletes now keep\n  recoverable prior versions.",
        events=[{"type": "bucket_versioning_enabled",
                 "bucket": bucket["slug"]}])


def bucket_events(bucket: dict) -> list[dict[str, Any]]:
    """The inspection events — exposure computed once, here. A
    remediated should-be-private bucket additionally emits
    `bucket_secured`, so verification means LOOKING again."""
    events: list[dict[str, Any]] = [{
        "type": "bucket_inspected",
        "bucket": bucket["slug"],
        "public": bucket["public"],
        "encrypted": bucket["encrypted"],
        "exposed": bucket["public"] and not bucket["intended_public"],
    }]
    if (not bucket["public"] and bucket["encrypted"]
            and not bucket["intended_public"]):
        events.append({"type": "bucket_secured", "bucket": bucket["slug"]})
    return events
