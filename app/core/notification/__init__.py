"""Universal Notification Framework (YC-031.6).

    from app.core.notification import (
        # Types
        NotificationData, NotificationType, Priority, UserPreferences,
        # Services
        send, send_bulk, mark_read, mark_all_read, delete,
        get_unread, get_notifications, notification_summary,
        # Auto-event helpers
        notify_achievement, notify_level_up, notify_certificate,
        notify_lab_completed, notify_assessment,
    )
"""

from app.core.notification.types import (  # noqa: F401
    NotificationData,
    NotificationType,
    Priority,
    UserPreferences,
)
from app.core.notification.services import (  # noqa: F401
    delete,
    get_notifications,
    get_unread,
    mark_all_read,
    mark_read,
    notification_summary,
    notify_achievement,
    notify_assessment,
    notify_certificate,
    notify_lab_completed,
    notify_level_up,
    send,
    send_bulk,
)
