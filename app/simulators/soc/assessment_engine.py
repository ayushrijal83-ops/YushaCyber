"""Blue Team Assessment scoring engine (YC-030.7).

Evaluates the entire assessment: alert prioritisation, evidence
quality, correct decisions, MITRE mapping, false-positive handling,
incident reports, and time taken. Produces a final grade.
"""

from __future__ import annotations

from typing import Any

GRADE_THRESHOLDS = {
    "Excellent": 0.90,
    "Pass": 0.65,
    "Needs Improvement": 0.40,
}


def score_assessment(state: dict[str, Any],
                     expected: dict[str, Any]) -> dict[str, Any]:
    """Compute the full assessment score.

    ``state`` is the simulator session state.
    ``expected`` is the scenario's answer key (from the seed).
    """
    scores: dict[str, int] = {}
    max_scores: dict[str, int] = {}

    # 1. Alert classification (20 pts max).
    classifications = state.get("classifications") or {}
    expected_cls = expected.get("classifications") or {}
    correct_cls = sum(1 for code, cls in classifications.items()
                      if expected_cls.get(code) == cls)
    scores["alert_prioritisation"] = min(20, correct_cls * 4)
    max_scores["alert_prioritisation"] = 20

    # 2. False-positive handling (15 pts max).
    expected_fp = {code for code, cls in expected_cls.items()
                   if cls == "false_positive"}
    student_fp = {code for code, cls in classifications.items()
                  if cls == "false_positive"}
    fp_correct = len(expected_fp & student_fp)
    fp_wrong = len(student_fp - expected_fp)
    scores["false_positives"] = max(0, min(15, fp_correct * 5 - fp_wrong * 3))
    max_scores["false_positives"] = 15

    # 3. Evidence quality — bookmarks + searches (15 pts max).
    bookmarks = len(state.get("hunt_bookmarks") or [])
    searches = len([s for s in (state.get("hunt_searches") or [])
                    if s.get("results", 0) > 0])
    scores["evidence"] = min(15, bookmarks * 2 + searches * 2)
    max_scores["evidence"] = 15

    # 4. MITRE mapping (15 pts max).
    mitre_mapped = len(state.get("hunt_mitre_mapped") or [])
    scores["mitre"] = min(15, mitre_mapped * 3)
    max_scores["mitre"] = 15

    # 5. IR decisions (15 pts max).
    decisions = state.get("ir_decisions") or []
    correct_decisions = sum(1 for d in decisions if d.get("correct"))
    scores["decisions"] = min(15, correct_decisions * 3)
    max_scores["decisions"] = 15

    # 6. Report quality (20 pts max).
    report = (state.get("report") or "").strip().lower()
    report_len = len(report)
    report_sections = sum(1 for s in (
        "executive summary", "timeline", "evidence",
        "root cause", "containment", "recovery",
        "recommendations", "mitre")
        if s in report)
    scores["report"] = min(20, (5 if report_len >= 200 else 0)
                           + report_sections * 2)
    max_scores["report"] = 20

    # Totals.
    total = sum(scores.values())
    max_total = sum(max_scores.values())
    hints_used = int(state.get("hints_used") or 0)
    total = max(0, total - hints_used * 3)
    ratio = total / max(1, max_total)

    if ratio >= GRADE_THRESHOLDS["Excellent"]:
        grade = "Excellent"
    elif ratio >= GRADE_THRESHOLDS["Pass"]:
        grade = "Pass"
    elif ratio >= GRADE_THRESHOLDS["Needs Improvement"]:
        grade = "Needs Improvement"
    else:
        grade = "Fail"

    return {
        "total": total,
        "max": max_total,
        "ratio": round(ratio, 2),
        "grade": grade,
        "breakdown": scores,
        "max_breakdown": max_scores,
        "hints_used": hints_used,
    }
