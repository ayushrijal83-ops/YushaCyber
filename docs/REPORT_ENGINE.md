# Universal Report Engine

## Architecture

```
app/core/report/
├── __init__.py      ← Public API (import from here)
├── types.py         ← Report, ReportSection, ReportKind,
│                       OutputFormat, SectionKind, SECTION_LABELS
├── models.py        ← report_from_dict(), report_from_state()
├── builder.py       ← ReportBuilder — fluent section-by-section API
├── templates.py     ← Default section orderings per report type
├── renderer.py      ← render() — Markdown, HTML, JSON output
├── export.py        ← export_html/markdown/json convenience wrappers
└── services.py      ← Public API: create_report(), build_report(),
                        render_report(), export_report(), report_summary()
```

## Report Lifecycle

1. **Create** — `create_report()` or `build_report()` (returns a builder)
2. **Build** — Add sections via the fluent builder API
3. **Render** — `render_report(report, "markdown")` → string
4. **Export** — `export_report(report, "html")` → string

## Builder Example

```python
from app.core.report import build_report

report = (build_report("Incident Report", "investigation")
          .add_executive_summary("A coordinated attack was detected...")
          .add_timeline([
              {"at": "02:00", "event": "VPN login from external IP"},
              {"at": "02:15", "event": "PowerShell beacon deployed"},
          ])
          .add_evidence([{"ref": "dns-log", "label": "DNS capture"}])
          .add_findings([{"finding": "C2 domain c2.storm.example"}])
          .add_root_cause("Phishing email led to credential theft.")
          .add_mitre([{"technique_id": "T1059.001",
                       "technique_name": "PowerShell"}])
          .add_containment("Isolated WS-07 and blocked C2 IPs.")
          .add_recovery("Restored from clean backups.")
          .add_recommendations(["Enable MFA", "Update firewall rules"])
          .set_score(85, "B", 200)
          .build())
```

## Rendering

```python
from app.core.report import render_report, export_report

md = render_report(report, "markdown")   # Markdown string
html = render_report(report, "html")     # HTML fragment
j = render_report(report, "json")        # JSON string
```

## Templates

8 built-in templates define default section orderings:

| Type | Sections |
|---|---|
| lab | summary, objectives, findings, recommendations |
| investigation | summary, timeline, evidence, findings, root cause, containment, recovery, recommendations |
| threat_hunt | summary, timeline, evidence, findings, mitre, recommendations |
| incident | summary, timeline, evidence, findings, root cause, mitre, containment, recovery, recommendations |
| blue_team | all sections including appendix |
| assessment | summary, objectives, findings, recommendations |
| completion | summary, objectives |
| certificate_summary | summary |

## Extension Guide

### Adding a new report type

1. Add the type to `ReportKind` enum in `types.py`
2. Add a template in `templates.py`
3. Use the builder to construct reports of that type

### Adding a new output format (e.g. PDF)

1. Add `PDF` to `OutputFormat` enum
2. Add `render_pdf()` in `renderer.py`
3. Add `export_pdf()` in `export.py`
4. Add the case to `render()` dispatch

### From session state (backward-compatible)

```python
from app.core.report import report_from_state

report = report_from_state(simulator_state,
                           report_type="investigation",
                           title="SOC Investigation")
```

This pulls the report text, score, MITRE mapping, bookmarks, and
timeline from the existing session state dict — works with every
SOC/Forensics/Hunt/Assessment report submission.
