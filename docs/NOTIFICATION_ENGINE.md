# Universal Notification Framework

## Architecture

```
app/core/notification/
├── __init__.py      ← Public API exports
├── types.py         ← NotificationData, NotificationType (11 types),
│                       Priority (4 levels), UserPreferences, DeliveryChannel
├── models.py        ← ORM bridge: notification_from_orm, notification_to_orm_kwargs
├── engine.py        ← CRUD: create, create_bulk, mark_read, mark_all_read,
│                       delete, get_unread, get_notifications, notification_summary
├── dispatcher.py    ← Multi-channel: InAppChannel (implemented),
│                       EmailChannel, PushChannel, WebhookChannel (interfaces)
├── templates.py     ← Message builders: achievement_unlocked, level_up,
│                       certificate_earned, lab_completed, assessment_passed/failed,
│                       daily_streak, xp_earned
├── preferences.py   ← Per-user settings: get/save_preferences, should_notify
└── services.py      ← Public API: send, send_bulk, mark_read, mark_all_read,
                        delete, get_unread, get_notifications, notification_summary,
                        notify_achievement, notify_level_up, notify_certificate,
                        notify_lab_completed, notify_assessment
```

## Notification Lifecycle

1. **Event** — achievement unlocked, lab completed, etc.
2. **Template** — message builder creates (title, message, type, link)
3. **Send** — `send()` persists to DB + dispatches to channels
4. **Display** — `get_unread()` / `notification_summary()` for the dropdown
5. **Mark read** — `mark_read()` / `mark_all_read()`

## Usage

```python
from app.core.notification import send, notify_achievement

# Direct send
send(user_id=1, title="Welcome!", message="Start learning.",
     ntype="system", link="/labs/")

# Auto-event helper
notify_achievement(user_id=1, title="SOC Rookie", xp=50)
```

## Delivery Channels

Only In-App is implemented. Email, Push, and Webhook are defined
as interfaces — add implementations when ready:

```python
class EmailChannel(DeliveryChannel):
    def deliver(self, notification):
        send_email(notification.user_id, notification.title, ...)
        return True
```

## User Preferences

Categories: achievements, xp, certificates, reminders, announcements, marketing.
Each can be toggled per user. Default: all on except marketing.

## Extension Guide

### Adding a new notification type

1. Add to `NotificationType` enum
2. Add a template function in `templates.py`
3. Add a helper in `services.py`

### Adding a delivery channel

1. Subclass `DeliveryChannel`
2. Implement `deliver()`
3. Add to `DEFAULT_CHANNELS` in `dispatcher.py`
