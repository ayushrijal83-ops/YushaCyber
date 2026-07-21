"""Notification Engine (YC-034.0).

One write path (`notify`) used by every other engine, plus two
SQLAlchemy ``after_insert`` listeners that turn achievement unlocks and
certificate issues into notifications WITHOUT touching the achievement
or certificate systems — a pure, additive hook on the ORM layer. The
listeners write through the flush connection, so the notification
lands in the same transaction as the unlock itself.
"""

from __future__ import annotations

from sqlalchemy import event as sa_event
from sqlalchemy import select

from app.community.models import Notification
from app.extensions import db


def notify(user_ids, type_: str, title: str, body: str = "",
           link: str = "") -> int:
    """Create one notification per user. Returns how many were sent."""
    unique_ids = [uid for uid in dict.fromkeys(user_ids) if uid]
    for user_id in unique_ids:
        db.session.add(Notification(
            user_id=user_id, type=type_, title=title[:160],
            body=body[:300], link=link[:255]))
    return len(unique_ids)


def unread_count(user_id: int) -> int:
    return Notification.query.filter_by(
        user_id=user_id, is_read=False).count()


def recent(user_id: int, limit: int = 6) -> list[Notification]:
    return (Notification.query.filter_by(user_id=user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit).all())


def mark_all_read(user_id: int) -> int:
    changed = Notification.query.filter_by(
        user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return changed


# ===========================================================================
# ORM listeners — achievements & certificates become notifications
# without a single change to those systems.
# ===========================================================================
_LISTENERS_INSTALLED = False


def install_listeners() -> None:
    """Idempotently attach the after_insert hooks."""
    global _LISTENERS_INSTALLED
    if _LISTENERS_INSTALLED:
        return
    from app.achievement.models import Achievement, UserAchievement
    from app.certificates.models import Certificate, UserCertificate

    def _on_achievement(_mapper, connection, target) -> None:
        title = connection.execute(
            select(Achievement.title)
            .where(Achievement.id == target.achievement_id)
        ).scalar()
        connection.execute(Notification.__table__.insert().values(
            user_id=target.user_id, type="achievement",
            title="Achievement unlocked! 🏆",
            body=f"You earned “{title}”." if title else "New achievement.",
            link="/dashboard/achievements", is_read=False,
            created_at=db.func.now(), updated_at=db.func.now()))

    def _on_certificate(_mapper, connection, target) -> None:
        title = connection.execute(
            select(Certificate.title)
            .where(Certificate.id == target.certificate_id)
        ).scalar()
        connection.execute(Notification.__table__.insert().values(
            user_id=target.user_id, type="certificate",
            title="Certificate earned! 📜",
            body=f"“{title}” has been issued to you."
            if title else "A certificate has been issued to you.",
            link="/dashboard/certificates", is_read=False,
            created_at=db.func.now(), updated_at=db.func.now()))

    sa_event.listen(UserAchievement, "after_insert", _on_achievement)
    sa_event.listen(UserCertificate, "after_insert", _on_certificate)
    _LISTENERS_INSTALLED = True
