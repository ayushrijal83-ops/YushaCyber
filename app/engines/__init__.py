"""Universal Scenario Engine (YC-031.0).

Reusable services that power every interactive learning module in
YushaCyber. These are higher-level wrappers around the existing
Lab / LabObjective / validator / session-manager primitives. All
existing labs keep working unchanged — these engines provide a
unified API that new modules adopt and existing modules can
gradually migrate to.

Submodules:
  · scenario_engine    — scenario definition, loading, completion check
  · objective_engine   — reusable objective types + helpers
  · validation_engine  — generic validator with new types
  · progress_engine    — per-session progress tracking
"""
