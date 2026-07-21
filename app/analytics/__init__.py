"""Learning Analytics & Instructor Dashboard (YC-033.0).

Read-only insight over the existing systems (auth, XP, roadmaps,
lessons, labs, CTF, certificates, achievements) — none of them are
modified, only queried. The single write path is the analytics-owned
event stream (hint tracking).

  · services.py — every aggregate calculation (reusable, template-free)
  · export.py   — CSV writers over PDF-ready payload builders
  · routes.py   — admin dashboard pages + the event endpoint
  · models.py   — AnalyticsEvent
"""

from app.analytics.routes import analytics_bp  # noqa: F401
