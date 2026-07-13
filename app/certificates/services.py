"""Certificate service layer.

Retrieval, unique code generation, and statistics. No issuing logic, PDF
generation, or UI here — this foundation ticket provides reads plus the
code generator the future issuing engine will use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.auth.models import User
from app.certificates.models import Certificate, UserCertificate
from app.extensions import db

_CODE_PREFIX = "YC"


def get_all_certificates() -> list[Certificate]:
    """All active certificates in display order."""
    return (
        Certificate.query
        .filter_by(is_active=True)
        .order_by(Certificate.display_order)
        .all()
    )


def get_certificate(slug: str) -> Optional[Certificate]:
    """One active certificate by slug, or None."""
    if not slug:
        return None
    return Certificate.query.filter_by(slug=slug, is_active=True).first()


def get_user_certificates(user: User) -> list[UserCertificate]:
    """A user's earned certificates, newest first."""
    if user is None:
        return []
    return (
        UserCertificate.query
        .filter_by(user_id=user.id)
        .order_by(UserCertificate.created_at.desc())
        .all()
    )


def has_certificate(user: User, certificate: Certificate) -> bool:
    """Whether the user has already earned this certificate."""
    if user is None or certificate is None:
        return False
    return (
        UserCertificate.query
        .filter_by(user_id=user.id, certificate_id=certificate.id)
        .first()
        is not None
    )


def generate_certificate_code() -> str:
    """Generate a unique certificate code like 'YC-2026-000001'.

    The numeric part is a zero-padded running sequence. The database's
    unique constraint on ``certificate_code`` is the source of truth; this
    function probes forward from the current count to find an unused code,
    so it stays correct even if rows were deleted or added concurrently.
    """
    year = datetime.now(timezone.utc).year
    base = UserCertificate.query.count() + 1
    while True:
        code = f"{_CODE_PREFIX}-{year}-{base:06d}"
        exists = (
            UserCertificate.query
            .filter_by(certificate_code=code)
            .first()
        )
        if exists is None:
            return code
        base += 1


def get_certificate_statistics(user: User) -> dict[str, int]:
    """Earned stats for a user: total, earned, remaining, percentage."""
    total = Certificate.query.filter_by(is_active=True).count()
    if user is None or total == 0:
        return {"total": total, "earned": 0, "remaining": total, "percentage": 0}

    earned = UserCertificate.query.filter_by(user_id=user.id).count()
    remaining = total - earned
    percentage = int(earned / total * 100) if total else 0
    return {
        "total": total,
        "earned": earned,
        "remaining": remaining,
        "percentage": percentage,
    }


# ===========================================================================
# Automatic issuing (YC-009.2)
# ===========================================================================
def _parse_slugs(raw: Optional[str]) -> list[str]:
    """Split a comma-separated slug string into a clean list."""
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def check_certificate_requirements(user: User, certificate: Certificate) -> bool:
    """Whether the user meets ALL of a certificate's requirements.

    Reuses existing services (no duplicated logic):
    - required_modules: every listed module slug must be completed
      (roadmap is_module_completed).
    - required_quizzes: every listed module's quiz must be passed
      (quiz_services has_passed_quiz).
    - required_xp: user.xp must be at least the threshold.

    Empty/absent requirements are treated as satisfied. Returns True only
    if every present requirement is met.
    """
    if user is None or certificate is None:
        return False

    from app.roadmap.services import get_module, is_module_completed
    from app.roadmap.quiz_services import get_module_quiz, has_passed_quiz

    # Module requirements.
    for slug in _parse_slugs(certificate.required_modules):
        module = get_module(slug)
        if module is None or not is_module_completed(user, module):
            return False

    # Quiz requirements (by module slug).
    for slug in _parse_slugs(certificate.required_quizzes):
        quiz = get_module_quiz(slug)
        if quiz is None or not has_passed_quiz(user, quiz):
            return False

    # XP requirement.
    if certificate.required_xp and (user.xp or 0) < certificate.required_xp:
        return False

    return True


def issue_certificate(user: User, certificate: Certificate) -> dict[str, Any]:
    """Issue a certificate to a user if earned and not already owned.

    Duplicate-safe (checks has_certificate and relies on the unique
    constraint) and requirement-gated. Generates a unique code, records a
    UserCertificate in one transaction, and rolls back on failure — never
    leaving a partial record. Does not itself re-check nothing else.

    Returns one of:
        {"issued": True,  "certificate": cert, "already_owned": False, "code": ...}
        {"issued": False, "already_owned": True,  "certificate": cert}
        {"issued": False, "reason": "requirements_not_met"}
        {"issued": False, "reason": "invalid"}
        {"issued": False, "reason": "persist_failed"}
    """
    if user is None or certificate is None or not certificate.is_active:
        return {"issued": False, "reason": "invalid"}

    if has_certificate(user, certificate):
        return {"issued": False, "already_owned": True, "certificate": certificate}

    if not check_certificate_requirements(user, certificate):
        return {"issued": False, "reason": "requirements_not_met"}

    try:
        code = generate_certificate_code()
        row = UserCertificate(
            user_id=user.id,
            certificate_id=certificate.id,
            certificate_code=code,
            issued_at=datetime.now(timezone.utc),
        )
        db.session.add(row)
        db.session.commit()
    except Exception:  # noqa: BLE001 — rollback on any persistence error
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception(
            "Failed to issue certificate %s to user %s",
            certificate.slug, user.id,
        )
        return {"issued": False, "reason": "persist_failed"}

    from flask import current_app
    current_app.logger.info(
        "Certificate issued: user=%s certificate=%s code=%s",
        user.id, certificate.slug, code,
    )
    return {"issued": True, "certificate": certificate,
            "already_owned": False, "code": code}


def check_all_certificates(user: User) -> dict[str, Any]:
    """Issue every certificate the user now qualifies for.

    Iterates active certificates, skips already-owned ones, and issues any
    whose requirements are satisfied. Returns {"issued": [Certificate, ...]}
    listing only certificates issued on THIS call.
    """
    result: dict[str, Any] = {"issued": []}
    if user is None:
        return result

    for certificate in get_all_certificates():
        if has_certificate(user, certificate):
            continue
        outcome = issue_certificate(user, certificate)
        if outcome.get("issued"):
            result["issued"].append(certificate)

    return result


# ===========================================================================
# Dashboard page context (YC-009.3) — preformatted for the certificates UI.
# Reuses retrieval + statistics services; no ORM leaks to the template.
# ===========================================================================
def _requirement_summary(certificate: Certificate) -> str:
    """Human-readable summary of what a certificate requires."""
    parts: list[str] = []
    mods = _parse_slugs(certificate.required_modules)
    quizzes = _parse_slugs(certificate.required_quizzes)
    if mods:
        parts.append(f"{len(mods)} module{'s' if len(mods) != 1 else ''}")
    if quizzes:
        parts.append(f"{len(quizzes)} quiz{'zes' if len(quizzes) != 1 else ''}")
    if certificate.required_xp:
        parts.append(f"{certificate.required_xp} XP")
    return "Requires " + ", ".join(parts) if parts else "No requirements"


def get_certificates_page_context(user: User) -> dict[str, Any]:
    """Everything the certificates page needs, preformatted.

    Returns {statistics, certificates, has_any_earned}. Each certificate is
    a plain dict with an ``earned`` flag plus code/issue-date when earned,
    or a requirement summary when locked — so the template renders without
    touching the ORM or computing anything.
    """
    stats = get_certificate_statistics(user)

    # Map certificate_id -> issued UserCertificate for this user (one query).
    issued: dict[int, Any] = {}
    if user is not None:
        for uc in UserCertificate.query.filter_by(user_id=user.id).all():
            issued[uc.certificate_id] = uc

    cards: list[dict[str, Any]] = []
    for c in get_all_certificates():
        uc = issued.get(c.id)
        earned = uc is not None
        when = (uc.issued_at or uc.created_at) if uc else None
        cards.append({
            "id": c.id,
            "title": c.title,
            "slug": c.slug,
            "description": c.description,
            "category": c.category,
            "icon": c.icon,
            "certificate_type": c.certificate_type,
            "earned": earned,
            "certificate_code": uc.certificate_code if uc else None,
            "issued_date": when.strftime("%b %d, %Y") if when else None,
            "requirement_summary": _requirement_summary(c),
        })

    return {
        "statistics": stats,
        "certificates": cards,
        "has_any_earned": stats["earned"] > 0,
        "nav_items": _certificates_nav_items(),
    }


def _certificates_nav_items() -> list:
    """Sidebar nav with the certificates item active (reuses dashboard nav)."""
    from app.dashboard.services import get_nav_items
    return get_nav_items(active="certificates")
