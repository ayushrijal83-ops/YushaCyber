"""Active Directory Security Lab package (YC-031.0).

Reusable enterprise-identity engines + the AD simulator plugin:

  · domains.py           — domain definitions (data) + schema validation
  · engine.py            — Domain Engine: build/query the directory
  · user_engine.py       — User Engine: resets, unlocks, enable/disable, moves
  · group_engine.py      — Group Engine: membership + least privilege
  · policy_engine.py     — Policy Engine: password/lockout/GPO simulation
  · permission_engine.py — Permission Engine: ACLs + Kerberos flow
  · simulator.py         — ADSimulator (key="ad") plugging into the Lab Engine
  · models.py            — admin-created custom domains
  · seed.py              — category, labs, objectives, achievements, certificate

Future enterprise labs (privilege escalation paths, GPO hardening,
tiered administration) import these engines — never reimplement them.
"""

from __future__ import annotations

from app.labs.ad.domains import (
    BUILTIN_DOMAINS,
    get_domain,
    list_domains,
    parse_domain_json,
    validate_domain_def,
)
from app.labs.ad.engine import build_directory, explorer_tree

__all__ = [
    "BUILTIN_DOMAINS",
    "build_directory",
    "explorer_tree",
    "get_domain",
    "list_domains",
    "parse_domain_json",
    "validate_domain_def",
]
