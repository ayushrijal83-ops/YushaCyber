# AI Analytics & Instructor Dashboard

## Architecture

```
app/core/ai/analytics/
├── models.py     ← AIUsageMetrics, StudentAnalytics, HintAnalytics,
│                    RecommendationAnalytics, LabAnalytics,
│                    AIHealthMetrics, DashboardData
├── collector.py  ← ORM collectors for each metric group
├── engine.py     ← Aggregation + 30s TTL caching
├── reports.py    ← daily/weekly/monthly/student report generation
├── charts.py     ← Data series for frontend charts
├── export.py     ← JSON + CSV export
└── services.py   ← Public API

Admin page: /admin/ai
API: /api/ai/admin/analytics, /report, /export, /charts
```

## Dashboard Sections

| Section | Metrics |
|---|---|
| AI Usage | Total conversations, messages today/week/month, avg tokens |
| Students | Active learners, avg XP/level, completion rate, needing help |
| Hints | Total requested, level distribution, success rate, XP lost |
| Recommendations | Generated, accepted, completion rate, weak/strong topics |
| Labs | Total, completion rate, most completed/abandoned |
| Health | Provider, model, status, error rate |

## Reports

- `GET /api/ai/admin/report?period=daily` — today's key metrics
- `GET /api/ai/admin/report?period=weekly` — week summary + trends
- `GET /api/ai/admin/report?period=monthly` — full summary

## Export

- `GET /api/ai/admin/export?dataset=all&format=json`
- `GET /api/ai/admin/export?dataset=students&format=csv`
- Datasets: all, ai_usage, students, hints, labs, recommendations, health

## Caching

Engine caches the full dashboard for 30 seconds. `refresh()` invalidates.

## Security

Every endpoint is admin-only. Students get 403.
