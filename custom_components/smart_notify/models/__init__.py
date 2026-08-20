"""Data models for Smart Notify."""

from __future__ import annotations

from .config import SmartNotifyConfig
from .delivery import DeliveryRecord
from .payload import NotificationPayload
from .queued_notification import QueuedNotification

__all__ = [
    "DeliveryRecord",
    "NotificationPayload",
    "QueuedNotification",
    "SmartNotifyConfig",
]
