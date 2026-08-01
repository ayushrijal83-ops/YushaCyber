# Intelligent Context Engine

## Architecture

```
app/core/ai/context_engine/
├── models.py     ← FullContext + 7 sub-contexts (User, Learning,
│                    Progress, Activity, Assessment, Achievement, Roadmap)
├── collector.py  ← ORM collectors: collect_user/learning/progress/
│                    achievements/assessment/roadmap
├── activity.py   ← Real-time activity tracker (in-memory)
├── progress.py   ← LearningProfile analyzer (weakest/strongest topic,
│                    hint dependency, completion speed)
├── builder.py    ← Merges all into FullContext, 10s TTL cache
├── tracker.py    ← Navigation history per session
├── session.py    ← Event hooks: on_page_visit, on_lab_start/complete,
│                    on_objective_complete, on_hint_used, on_answer_submitted
└── services.py   ← Public API: get_context, get_context_dict,
                     get_context_summary, get_learning_profile, filter_for_ai
```

## Context Flow

1. Student opens a lab page
2. `on_page_visit(user_id, path, lab=slug)` records the activity
3. Student sends a chat message
4. `get_context(user, current_lab)` builds `FullContext`:
   - Reads User + Progress + Achievements + Assessment from ORM
   - Reads Activity + Session from in-memory trackers
   - Caches for 10 seconds
5. `summary_text()` generates a human-readable summary
6. Injected into the system prompt automatically

## Caching

`builder.py` caches per user_id with a 10-second TTL. Volatile
fields (current_lab, activity) are updated from cache. Cache is
invalidated on lab start, objective complete, and lab complete.

## Security

`filter_for_ai()` recursively removes: api_key, password, secret,
token, correct_answer, solution, instructor_notes. Called before
any context is sent to the AI provider or returned from the debug
endpoint.

## Debug Endpoint

`GET /api/ai/context` — admin only. Returns the current filtered
context dict for the logged-in user.

## Performance

Target: <100ms. Achieved via 10s caching + in-memory activity
tracker. ORM queries only fire once per 10 seconds per user.
