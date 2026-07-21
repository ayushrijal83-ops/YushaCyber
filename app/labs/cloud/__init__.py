"""Cloud Security Lab package (YC-032.0).

A fully simulated cloud provider for security education. Reusable
engines, one Simulator plugin, a built-in scenario account and an
admin Scenario Builder:

  · accounts.py        — account definitions + validation (data layer)
  · engine.py          — Cloud Engine: deployment state, lookups, audit
  · iam_engine.py      — IAM Engine: identities, roles, permissions
  · storage_engine.py  — Storage Engine: buckets, access, encryption
  · network_engine.py  — Networking Engine: VPCs, SGs, DB exposure
  · policy_engine.py   — Policy Engine: password policy, risk library
  · simulator.py       — the Lab Engine plugin (key "cloud")
  · models.py          — CloudCustomScenario (admin-authored accounts)
  · seed.py            — the six-lab Cloud Security track

No AWS. No Azure. No GCP. Nothing leaves the simulation.
"""

from app.labs.cloud import (  # noqa: F401
    accounts,
    engine,
    iam_engine,
    network_engine,
    policy_engine,
    storage_engine,
)
