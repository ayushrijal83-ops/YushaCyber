# Universal Analytics Engine

## Architecture

```
app/core/analytics/
├── __init__.py      ← Public API exports
├── types.py         ← StudentMetrics, TrackMetrics, AssessmentMetrics,
│                       EngagementMetrics, AdminDashboard, Insight
├── metrics.py       ← Pure computation: completion_rate, average,
│                       grade_from_scores, grade/score/difficulty
│                       distribution, pass_fail_rates
├── aggregator.py    ← Builds typed dataclasses from raw data dicts
├── engine.py        ← Insight generation (rule-based) + export (JSON, CSV)
├── models.py        ← ORM bridge: student_data_from_user, admin_data
└── services.py      ← Public API: student_summary, track_summary,
                        assessment_summary, engagement_summary,
                        admin_summary, insights_for_student/track,
                        export_analytics_json/csv
```

## Metric Definitions

| Metric | Type | Description |
|---|---|---|
| total_xp | int | Lifetime XP earned |
| completion_rate | float | completed_labs / total_labs |
| average_score | float | Mean score across assessments |
| average_grade | str | Grade letter from average score |
| current_streak | int | Consecutive days active |
| pass_rate | float | Passed attempts / total attempts |
| grade_distribution | dict | Count per grade letter |

## Insight Generation

Rule-based: each rule checks a metric against a threshold and
generates an Insight with category, severity, and message.

Built-in rules: low completion (<30%), excellent completion (>=90%),
frequent hints (>20), fast completion (<300s), many perfect scores
(>5), long streak (>=7 days).

## Export

```python
from app.core.analytics import export_analytics_json, export_analytics_csv

json_str = export_analytics_json(student_metrics)
csv_str = export_analytics_csv([row1.to_dict(), row2.to_dict()])
```

## Extension Guide

### Adding a new metric

Add a field to the appropriate dataclass in `types.py`, add the
computation in `metrics.py`, wire it in `aggregator.py`.

### Adding a new insight rule

Append to `INSIGHT_RULES` in `engine.py`:

```python
{"key": "metric_name", "op": ">", "threshold": 10,
 "severity": "warning",
 "message": "{username} has high {metric_name} ({metric_name})."}
```

### From ORM (needs app context)

```python
from app.core.analytics import student_summary_from_user, admin_summary

student = student_summary_from_user(user)
admin = admin_summary()  # auto-fetches from DB
```
