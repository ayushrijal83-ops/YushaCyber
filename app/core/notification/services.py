"""Notification services — the public API.

Every module calls these instead of reaching into submodules.
"""

from __future__ import annotations

from typing import Any

from app.core.notification import engine
from app.core.notification.dispatcher import dispatch
from app.core.notification.types import NotificationData


def send(user_id: int, title: str, message: str = "",
         ntype: str = "system", link: str = "",
         category: str = "",
         metadata: dict[str, Any] | None = None
         ) -> NotificationData:
    """Create + dispatch a notification."""
    data = engine.create(user_id, title, message, ntype, link,
                         category, metadata)
    dispatch(data)
    return data


def send_bulk(user_ids: list[int], title: str,
              message: str = "", ntype: str = "system",
              link: str = "") -> int:
    """Broadcast to multiple users. Returns count."""
    return engine.create_bulk(user_ids, title, message, ntype, link)


def mark_read(notification_id: int) -> bool:
    return engine.mark_read(notification_id)


def mark_all_read(user_id: int) -> int:
    return engine.mark_all_read(user_id)


def delete(notification_id: int) -> bool:
    return engine.delete(notification_id)


def get_unread(user_id: int, limit: int = 20
               ) -> list[NotificationData]:
    return engine.get_unread(user_id, limit)


def get_notifications(user_id: int, limit: int = 50,
                      include_read: bool = True
                      ) -> list[NotificationData]:
    return engine.get_notifications(user_id, limit, include_read)


def notification_summary(user_id: int) -> dict[str, Any]:
    return engine.notification_summary(user_id)


# ---------------------------------------------------------------------------
# Auto-event helpers (call from achievement/lab/certificate services)
# ---------------------------------------------------------------------------
def notify_achievement(user_id: int, title: str,
                       xp: int = 0) -> NotificationData:
    from app.core.notification.templates import achievement_unlocked
    t, m, nt, lk = achievement_unlocked(title, xp)
    return send(user_id, t, m, nt, lk, "achievements")


def notify_level_up(user_id: int, new_level: int) -> NotificationData:
    from app.core.notification.templates import level_up
    t, m, nt, lk = level_up(new_level)
    return send(user_id, t, m, nt, lk, "xp")


def notify_certificate(user_id: int,
                        cert_title: str) -> NotificationData:
    from app.core.notification.templates import certificate_earned
    t, m, nt, lk = certificate_earned(cert_title)
    return send(user_id, t, m, nt, lk, "certificates")


def notify_lab_completed(user_id: int, lab_title: str,
                         xp: int = 0) -> NotificationData:
    from app.core.notification.templates import lab_completed
    t, m, nt, lk = lab_completed(lab_title, xp)
    return send(user_id, t, m, nt, lk, "achievements")


def notify_assessment(user_id: int, title: str,
                      passed: bool, grade: str = ""
                      ) -> NotificationData:
    from app.core.notification.templates import (
        assessment_passed, assessment_failed)
    if passed:
        t, m, nt, lk = assessment_passed(title, grade)
    else:
        t, m, nt, lk = assessment_failed(title)
    return send(user_id, t, m, nt, lk, "achievements")
