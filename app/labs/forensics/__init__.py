"""Digital Forensics Lab package (YC-029.5.2).

A fully simulated forensic workstation for security education.
Reusable engine, one Simulator plugin, and admin-editable cases:

  · models.py      — ForensicsCase, ForensicsEvidence, ForensicsTimelineEvent
  · engine.py      — deterministic simulated hashes, metadata panel
                     builder, findings validator (pure functions)
  · simulator.py   — the Lab Engine plugin (key "forensics")
  · seed.py        — the "Missing Files" case + first lab

Nothing here touches the host filesystem. No real hashing tool is
called. Hashes are deterministic simulated strings so students see
plausible-looking artefacts they can compare.
"""

from app.labs.forensics import engine, models, simulator  # noqa: F401
