"""Certificate engine — reusable certificate issuing.

Wraps the existing ``app/certificates/services`` into a unified API.
Supports completion, track, assessment, and future professional certs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CertificateRequest:
    """Everything needed to issue a certificate."""
    certificate_slug: str = ""
    student_id: int | None = None
    score: int = 0
    grade: str = ""
    passed: bool = False


@dataclass
class CertificateResult:
    """Result of a certificate issuance attempt."""
    issued: bool = False
    already_owned: bool = False
    certificate_slug: str = ""
    certificate_code: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def issue_if_passed(request: CertificateRequest) -> CertificateResult:
    """Issue a certificate if the student passed.

    Wraps the existing ``app/certificates/services.issue_certificate``.
    Returns a CertificateResult regardless of outcome.
    """
    if not request.passed:
        return CertificateResult(
            issued=False,
            certificate_slug=request.certificate_slug,
            reason="not_passed")

    try:
        from app.auth.models import User
        from app.certificates.models import Certificate
        from app.certificates.services import issue_certificate

        user = User.query.get(request.student_id)
        cert = Certificate.query.filter_by(
            slug=request.certificate_slug).first()
        if user is None or cert is None:
            return CertificateResult(
                issued=False,
                certificate_slug=request.certificate_slug,
                reason="not_found")

        result = issue_certificate(user, cert)
        if result.get("issued"):
            return CertificateResult(
                issued=True,
                certificate_slug=request.certificate_slug,
                certificate_code=result.get("code", ""))
        if result.get("already_owned"):
            return CertificateResult(
                issued=False,
                already_owned=True,
                certificate_slug=request.certificate_slug,
                reason="already_owned")
        return CertificateResult(
            issued=False,
            certificate_slug=request.certificate_slug,
            reason=result.get("reason", "unknown"))
    except Exception:
        return CertificateResult(
            issued=False,
            certificate_slug=request.certificate_slug,
            reason="error")


def check_all_for_user(student_id: int) -> list[CertificateResult]:
    """Check and issue all eligible certificates for a user."""
    try:
        from app.auth.models import User
        from app.certificates.services import check_all_certificates
        user = User.query.get(student_id)
        if user is None:
            return []
        result = check_all_certificates(user)
        issued = result.get("issued") or []
        return [
            CertificateResult(issued=True,
                              certificate_slug=getattr(c, "slug", ""))
            for c in issued
        ]
    except Exception:
        return []
