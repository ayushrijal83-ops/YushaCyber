# Universal Assessment Engine

## Architecture

```
app/core/assessment/
├── __init__.py      ← Public API (import from here)
├── types.py         ← AssessmentResult, XPConfig, GradeThreshold,
│                       CertificateType, grade_from_ratio,
│                       DEFAULT_GRADE_SCALE, PASS_FAIL_SCALE
├── models.py        ← Builder: assessment_from_lab_progress()
├── grading.py       ← GradingInput, GradingWeights, calculate_grade()
├── engine.py        ← create, score, complete lifecycle helpers
├── certificate.py   ← CertificateRequest, CertificateResult,
│                       issue_if_passed() — wraps app/certificates/
├── analytics.py     ← analytics_summary() — aggregate stats
└── services.py      ← Public API:
                        create_assessment(), complete_assessment(),
                        calculate_grade(), calculate_xp(),
                        issue_certificate(), assessment_summary(),
                        analytics_summary()
```

## How It Works

The Assessment Engine wraps existing grading, XP, certificate, and
achievement services into one unified API. It does NOT replace the
existing code — it provides a higher-level interface.

### Grade Calculation

```python
from app.core.assessment import GradingInput, calculate_grade

result = calculate_grade(GradingInput(
    correct=9, total=10,
    completed_objectives=5, total_objectives=5,
    hints_used=2, hint_penalty_pct=0.03))
# → {grade: "B", final_ratio: 0.82, passed: True, ...}
```

### XP Calculation

```python
from app.core.assessment import XPConfig, calculate_xp

cfg = XPConfig(base_xp=200, difficulty_multiplier=1.5,
               perfect_bonus=50, hint_penalty_per=5)
xp = calculate_xp(cfg, score_ratio=0.95, hints_used=1)
# → {base: 300, perfect_bonus: 0, hint_penalty: 5, total: 295}
```

### Full Assessment Lifecycle

```python
from app.core.assessment import create_assessment, complete_assessment

a = create_assessment(scenario_id=lab.id, student_id=user.id)
a = complete_assessment(a, raw_score=85, max_score=100,
                        time_seconds=3600)
# a.grade = "B", a.passed = True, a.final_score = 85
```

### Configurable Grade Scales

```python
from app.core.assessment import GradeThreshold, grade_from_ratio

custom = [
    GradeThreshold("Gold", 0.90),
    GradeThreshold("Silver", 0.70),
    GradeThreshold("Bronze", 0.0),
]
grade_from_ratio(0.85, custom)  # → "Silver"
```

Two built-in scales: `DEFAULT_GRADE_SCALE` (A+ through F) and
`PASS_FAIL_SCALE` (Excellent / Pass / Needs Improvement / Fail).

### Analytics

```python
from app.core.assessment import analytics_summary, AssessmentResult

stats = analytics_summary([result1, result2, result3])
# → {average_score, highest_score, pass_rate, total_xp_earned, ...}
```

## Extension Guide

### Adding a new grade scale

Define a list of `GradeThreshold` objects sorted by `min_ratio`
descending. Pass it to `grade_from_ratio()` or `complete_assessment()`.

### Adding a new XP formula

Create an `XPConfig` with custom weights. The `calculate()` method
handles base × multiplier + bonuses − penalties automatically.

### Integrating a new module

1. Call `create_assessment()` when the student starts.
2. Track progress via the Scenario Engine (`app/core/scenario/`).
3. Call `complete_assessment()` when they finish.
4. Call `issue_certificate()` if they passed.

## Migration Strategy

Existing modules keep working unchanged. To migrate:
1. Replace ad-hoc scoring with `calculate_grade(GradingInput(...))`.
2. Replace ad-hoc XP with `calculate_xp(XPConfig(...), ...)`.
3. Replace direct certificate calls with `issue_certificate()`.

No database changes required — the engine operates on in-memory
dataclasses and delegates persistence to existing services.
