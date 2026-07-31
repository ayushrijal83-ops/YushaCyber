"""Notification engine — core CRUD + query operations.

Operates on the existing ORM ``Notification`` table via the bridge
in ``models.py``. No new tables required.
"""

from __future__ import annotations

from typing import Any

from app.core.notification.models import (
    notification_from_orm,
    notification_to_orm_kwargs,
)
from app.core.notification.types import NotificationData, TYPE_PRIORITY


def create(user_id: int, title: str, message: str = "",
           ntype: str = "system", link: str = "",
           category: str = "",
           metadata: dict[str, Any] | None = None
           ) -> NotificationData:
    """Create and persist a notification."""
    from app.community.models import Notification
    from app.extensions import db

    data = NotificationData(
        user_id=user_id, title=title, message=message,
        type=ntype, priority=TYPE_PRIORITY.get(ntype, "normal"),
        category=category, link=link, metadata=metadata or {})
    row = Notification(**notification_to_orm_kwargs(data))
    db.session.add(row)
    db.session.flush()
    data.id = row.id
    data.created_at = str(row.created_at) if row.created_at else ""
    return data


def create_bulk(user_ids: list[int], title: str,
                message: str = "", ntype: str = "system",
                link: str = "") -> int:
    """Send the same notification to many users. Returns count."""
    from app.community.models import Notification
    from app.extensions import db

    count = 0
    for uid in user_ids:
        kwargs = notification_to_orm_kwargs(NotificationData(
            user_id=uid, title=title, message=message,
            type=ntype, link=link))
        db.session.add(Notification(**kwargs))
        count += 1
    db.session.flush()
    return count


def mark_read(notification_id: int) -> bool:
    """Mark a single notification as read."""
    from app.community.models import Notification
    from app.extensions import db

    row = Notification.query.get(notification_id)
    if row is None:
        return False
    row.is_read = True
    db.session.flush()
    return True


def mark_all_read(user_id: int) -> int:
    """Mark all unread notifications for a user. Returns count."""
    from app.community.models import Notification
    from app.extensions import db

    rows = Notification.query.filter_by(
        user_id=user_id, is_read=False).all()
    for r in rows:
        r.is_read = True
    db.session.flush()
    return len(rows)


def delete(notification_id: int) -> bool:
    from app.community.models import Notification
    from app.extensions import db

    row = Notification.query.get(notification_id)
    if row is None:
        return False
    db.session.delete(row)
    db.session.flush()
    return True


def get_unread(user_id: int, limit: int = 20
               ) -> list[NotificationData]:
    from app.community.models import Notification
    rows = (Notification.query
            .filter_by(user_id=user_id, is_read=False)
            .order_by(Notification.created_at.desc())
            .limit(limit).all())
    return [notification_from_orm(r) for r in rows]


def get_notifications(user_id: int, limit: int = 50,
                      include_read: bool = True
                      ) -> list[NotificationData]:
    from app.community.models import Notification
    q = Notification.query.filter_by(user_id=user_id)
    if not include_read:
        q = q.filter_by(is_read=False)
    rows = q.order_by(Notification.created_at.desc()).limit(limit).all()
    return [notification_from_orm(r) for r in rows]


def unread_count(user_id: int) -> int:
    from app.community.models import Notification
    return Notification.query.filter_by(
        user_id=user_id, is_read=False).count()


def notification_summary(user_id: int) -> dict[str, Any]:
    """Quick summary for the notification dropdown."""
    unread = get_unread(user_id, limit=5)
    return {
        "unread_count": unread_count(user_id),
        "recent": [n.to_dict() for n in unread],
    }
