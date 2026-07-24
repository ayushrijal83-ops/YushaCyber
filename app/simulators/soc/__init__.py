"""SOC Analyst Simulator (YC-030.1).

Foundation for the Security Operations Center track. Reuses every
Digital Forensics engine (Timeline, Evidence, Metadata, Hash, Artifact,
Correlation) — nothing there is duplicated. What this package adds:

  · models.py       — SocAlert + SocPlaybook + SocPlaybookStep +
                      SocChecklistItem
  · dashboard.py    — analyst dashboard aggregates over the alert queue
  · alerts.py       — alert lookups, filters, IR envelope helpers
  · playbooks.py    — playbook lookup / rendering
  · report_engine.py — SOC-report validation (extends the forensics
                      findings validator with playbook + root-cause
                      checks)
  · services.py     — orchestrates alert investigation flow
  · simulator.py    — the Lab Engine plugin (key "soc")
  · seed.py         — seeds the roadmap category, playbooks, alerts,
                      first lab and the SOC Rookie achievement

Alerts investigate an underlying ``ForensicsCase`` — the whole
evidence / source / timeline / correlation UX flows straight through.
"""

from app.simulators.soc import models, simulator  # noqa: F401
