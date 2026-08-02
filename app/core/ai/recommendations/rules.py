"""Recommendation rules — prerequisite + security checks."""

from __future__ import annotations


def prerequisites_met(lab, completed_slugs: set[str]) -> bool:
    """Check if a lab's prerequisites are satisfied."""
    if not lab.prerequisite_lab_id:
        return True
    try:
        from app.labs.models import Lab
        prereq = Lab.query.get(lab.prerequisite_lab_id)
        if prereq and prereq.slug in completed_slugs:
            return True
    except Exception:
        pass
    return False


def is_recommendable(lab) -> bool:
    """Check if a lab should appear in recommendations."""
    if not lab.is_active:
        return False
    return True
