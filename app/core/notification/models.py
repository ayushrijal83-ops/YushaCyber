"""Notification models — ORM bridge.

Wraps the existing ``app/community/models.Notification`` into the
framework's ``NotificationData`` dataclass. No new tables.
"""

from __future__ import annotations

from typing import Any

from app.core.notification.types import NotificationData, TYPE_PRIORITY


def notification_from_orm(row) -> NotificationData:
    """Convert an ORM Notification row to NotificationData."""
    return NotificationData(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        message=getattr(row, "body", "") or "",
        type=row.type,
        priority=TYPE_PRIORITY.get(row.type, "normal"),
        link=getattr(row, "link", "") or "",
        created_at=str(row.created_at) if row.created_at else "",
        read_at=str(row.updated_at) if getattr(row, "is_read", False) else None,
    )


def notification_to_orm_kwargs(data: NotificationData) -> dict[str, Any]:
    """Convert NotificationData to kwargs for ORM Notification()."""
    return {
        "user_id": data.user_id,
        "type": data.type,
        "title": data.title[:160],
        "body": data.message[:300],
        "link": data.link[:255],
        "is_read": data.is_read,
    }
