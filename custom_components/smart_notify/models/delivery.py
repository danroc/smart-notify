"""Delivery attempt record model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    """Record of a delivery attempt."""

    notification_id: str
    recipients: list[str]
    services: list[str]
    delivered_at: datetime
    success: bool
    error: str | None = None
