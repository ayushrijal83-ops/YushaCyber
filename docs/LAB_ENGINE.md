# Interactive Cyber Lab Engine

## Architecture

```
app/core/lab_engine/
├── types.py      ← LabDef, LabObjectiveDef, Workspace, LabType (13),
│                    ObjectiveKind (9), EventKind (8)
├── registry.py   ← register_lab(), register_workspace(), get_lab(),
│                    list_labs() — plug in new types without modifying engine
├── objective.py  ← check() — validates submissions against objectives
├── events.py     ← EventLog — per-session event log
├── progress.py   ← LabProgress — completion %, XP, hints, attempts
├── state.py      ← In-memory save/load/reset
├── workspace.py  ← Abstract workspace lifecycle
├── session.py    ← LabSession — isolated per-student session
├── engine.py     ← Orchestrator: start, submit, hint, reset, ai_context
└── services.py   ← Public API
```

## How it works

1. Register a lab definition: `register_lab(LabDef(...))`
2. Register a workspace factory: `register_workspace("linux", factory)`
3. Student starts: `start_lab(user_id, slug)` → LabSession
4. Student submits: `submit_objective(user_id, slug, "o1", "pwd")` → result
5. Auto-saves after every submission
6. XP awarded via existing User model
7. AI gets context: `get_ai_context(user_id, slug)`

## Adding a new lab type

```python
from app.core.lab_engine import register_lab, register_workspace, LabDef, LabObjectiveDef, Workspace

# 1. Register workspace factory
def create_terminal(config):
    return Workspace(workspace_type="linux", config=config)
register_workspace("linux", create_terminal)

# 2. Register lab
register_lab(LabDef(
    slug="linux-basics", title="Linux Basics", lab_type="linux",
    objectives=[
        LabObjectiveDef(id="1", title="Run pwd", kind="run_command", expected="pwd", xp=25),
    ],
))
```

## Integrations

- **XP**: Awards via existing `User.xp` on objective completion
- **AI Mentor**: `ai_context()` returns current lab state for CyberMentor
- **Achievements**: Future — hook into events
- **Validation**: Extensible `check()` function
