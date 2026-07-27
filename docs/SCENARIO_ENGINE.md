# Universal Scenario Engine

## Architecture

```
app/core/scenario/
├── __init__.py      ← Public API (import from here)
├── types.py         ← Enums: Difficulty, Grade, ObjectiveType,
│                       ReportType, ValidationRule
├── models.py        ← Scenario + Objective dataclasses,
│                       scenario_from_lab(), scenario_from_dict()
├── engine.py        ← Pure logic: is_complete(), completion_ratio(),
│                       compute_grade(), next_objective()
├── validator.py     ← validate(), validate_all() — wraps the
│                       existing VALIDATOR_REGISTRY
├── progress.py      ← Progress dataclass, calculate(),
│                       objectives_summary()
└── services.py      ← Public service API:
                        load_scenario(), complete_objective(),
                        validate_submission(), calculate_progress(),
                        award_xp(), generate_report()
```

## How It Works

The Scenario Engine wraps the existing `Lab` / `LabObjective` /
`VALIDATOR_REGISTRY` / `session_manager` infrastructure into one
unified API. It does NOT replace the existing code — it provides a
higher-level interface that new modules adopt and existing modules
can gradually migrate to.

**Data flow:**

```
ORM Lab row  ──→  scenario_from_lab()  ──→  Scenario dataclass
                                              │
Plain dict   ──→  scenario_from_dict() ──→    │
                                              ▼
                                     services.load_scenario()
                                              │
                    ┌─────────────────────────┼─────────────────┐
                    ▼                         ▼                 ▼
            calculate_progress()    validate_submission()   award_xp()
                    │                         │                 │
                    ▼                         ▼                 ▼
               Progress              {validator: bool}    user.xp += n
```

## Quick Start

### Loading a scenario

```python
from app.core.scenario import load_scenario

# From an ORM Lab row:
from app.labs.models import Lab
lab = Lab.query.filter_by(slug="forensics-fundamentals").first()
scenario = load_scenario(lab)

# From a plain dict:
scenario = load_scenario({
    "slug": "my-custom-lab",
    "title": "Custom Investigation",
    "difficulty": "Medium",
    "xp_reward": 100,
    "objectives": [
        {
            "id": 1,
            "title": "Find the IOC",
            "validator_type": "event_emitted",
            "validator_data": {"event": "ioc_found"},
            "xp_reward": 25,
        },
    ],
})
```

### Tracking progress

```python
from app.core.scenario import calculate_progress

progress = calculate_progress(scenario, completed_ids={1, 2})
print(progress.ratio)    # 0.5
print(progress.status)   # "in_progress"
print(progress.grade)    # "Fail" (not complete yet)
```

### Completing objectives

```python
from app.core.scenario import complete_objective

result = complete_objective(user, lab, objective_id=1)
# {"ok": True, "already_completed": False, "xp": 25}
```

### Validating submissions

```python
from app.core.scenario import validate_submission

results = validate_submission(scenario, state={"answer": "42"})
# {"exact_match": True}
```

### Generating reports

```python
from app.core.scenario import generate_report, calculate_progress

progress = calculate_progress(scenario, {1, 2, 3})
report = generate_report(scenario, progress, state)
# {"scenario": {...}, "progress": {...}, "score": {...}, ...}
```

## Supported Objective Types

| Type | Enum | Description |
|------|------|-------------|
| Visit Page | `visit_page` | Student opens a panel/tab |
| Inspect Evidence | `inspect_evidence` | Student examines evidence |
| Execute Command | `execute_command` | Student runs a simulated command |
| Answer Question | `answer_question` | Student provides a specific answer |
| Identify IOC | `identify_ioc` | Student finds an indicator of compromise |
| Complete Timeline | `complete_timeline` | Student reconstructs a timeline |
| Write Report | `write_report` | Student submits a written report |
| Upload Finding | `upload_finding` | Student uploads analysis results |
| Custom | `custom` | Any module-specific objective |

## Supported Validators

| Validator | Description |
|-----------|-------------|
| `exact_command` | Command string matches exactly |
| `regex_command` | Command matches a regex pattern |
| `output_contains` | Simulator output contains a string |
| `state_flag` | A state value equals an expected value |
| `event_emitted` | A specific event was fired |
| `exact_match` | Case-insensitive string comparison |
| `multi_step` | Multiple events all fired (any order) |
| `ordered_tasks` | Events fired in a specific order |
| `score_threshold` | A numeric value meets a minimum |
| `custom_hook` | Delegates to a named Python function |

## Extension Guide

### Adding a new module

1. Seed your lab data as usual (Lab + LabObjective rows).
2. Load it: `scenario = load_scenario(lab)`.
3. Track progress: `calculate_progress(scenario, completed_ids)`.
4. Award XP: `award_xp(user, amount)`.
5. Generate report: `generate_report(scenario, progress)`.

### Adding a new objective type

1. Add it to `ObjectiveType` in `types.py`.
2. Register a validator in `app/labs/validator.py` or
   `app/engines/validation_engine.py`.
3. Use it in seed code:
   ```python
   from app.core.scenario.types import ValidationRule
   rule = ValidationRule("my_validator", {"key": "value"})
   ```

### Adding a new validator

```python
# In app/engines/validation_engine.py:
from app.labs.validator import register_validator, ValidationContext

@register_validator("my_validator")
def _my_validator(spec: dict, ctx: ValidationContext) -> bool:
    return ctx.state_value(spec["path"]) == spec["expected"]
```

## Migration Plan

### Phase 1 (Complete — YC-031.0 + YC-031.1)
- Core engine created at `app/core/scenario/`
- All existing labs work unchanged via `scenario_from_lab()`
- 10 validators registered (5 original + 5 new)

### Phase 2 (Future)
- New modules (AD, Cloud, API Security) use `app/core/scenario/`
  as their primary API from day one
- Existing seed code gradually adopts `ValidationRule` constructors
  instead of raw dicts

### Phase 3 (Future)
- Admin UI uses `Scenario.to_dict()` for a universal scenario editor
- Progress API powers a unified student dashboard across all modules
