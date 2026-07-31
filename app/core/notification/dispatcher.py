"""Notification dispatcher — multi-channel delivery.

Currently only In-App is implemented. Email, Push, and Webhook
channels are defined as interfaces for future expansion.
"""

from __future__ import annotations


from app.core.notification.types import DeliveryChannel, NotificationData


class InAppChannel(DeliveryChannel):
    """Delivers via the existing ORM Notification table."""
    name: str = "in_app"

    def deliver(self, notification: NotificationData) -> bool:
        # Already persisted by engine.create — nothing extra needed.
        return True


class EmailChannel(DeliveryChannel):
    """Future email delivery (interface only)."""
    name: str = "email"
    enabled: bool = False

    def deliver(self, notification: NotificationData) -> bool:
        # Placeholder — integrate with email service later.
        return False


class PushChannel(DeliveryChannel):
    """Future push notification (interface only)."""
    name: str = "push"
    enabled: bool = False

    def deliver(self, notification: NotificationData) -> bool:
        return False


class WebhookChannel(DeliveryChannel):
    """Future webhook delivery (interface only)."""
    name: str = "webhook"
    enabled: bool = False

    def deliver(self, notification: NotificationData) -> bool:
        return False


# Default channel set.
DEFAULT_CHANNELS: list[DeliveryChannel] = [InAppChannel()]


def dispatch(notification: NotificationData,
             channels: list[DeliveryChannel] | None = None
             ) -> dict[str, bool]:
    """Deliver a notification through all enabled channels."""
    channels = channels or DEFAULT_CHANNELS
    results: dict[str, bool] = {}
    for ch in channels:
        if ch.enabled:
            results[ch.name] = ch.deliver(notification)
    return results
