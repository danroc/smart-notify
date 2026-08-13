"""Data models for Smart Notify."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
    DEFAULT_EXPIRE_AFTER,
    DEFAULT_PRIORITY,
    DEFAULT_STRATEGY,
    DEFAULT_TOLERANCE,
    QUEUE_STATUS_PENDING,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class NotificationPayload:
    """Immutable notification payload."""

    id: str
    title: str | None
    message: str
    strategy: str
    priority: str
    tag: str | None
    payload: dict[str, Any]
    created: datetime
    expires: datetime
    metadata: dict[str, Any]
    tolerance: int | None = None
    queue_if_no_candidate: bool = True
    channels: list[str] | None = None
    persons: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "strategy": self.strategy,
            "priority": self.priority,
            "tag": self.tag,
            "payload": self.payload,
            "created": self.created.isoformat(),
            "expires": self.expires.isoformat(),
            "metadata": self.metadata,
            "tolerance": self.tolerance,
            "queue_if_no_candidate": self.queue_if_no_candidate,
            "channels": self.channels,
            "persons": self.persons,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotificationPayload:
        """Deserialize from storage."""
        return cls(
            id=data["id"],
            title=data.get("title"),
            message=data["message"],
            strategy=data["strategy"],
            priority=data.get("priority", DEFAULT_PRIORITY),
            tag=data.get("tag"),
            payload=data.get("payload", {}),
            created=dt_util.parse_datetime(data["created"]) or dt_util.utcnow(),
            expires=dt_util.parse_datetime(data["expires"]) or dt_util.utcnow(),
            metadata=data.get("metadata", {}),
            tolerance=data.get("tolerance"),
            queue_if_no_candidate=data.get("queue_if_no_candidate", True),
            channels=data.get("channels"),
            persons=data.get("persons"),
        )


@dataclass(slots=True)
class QueuedNotification:
    """A notification stored in the persistent queue."""

    id: str
    created: datetime
    expires: datetime
    strategy: str
    payload: NotificationPayload
    status: str = QUEUE_STATUS_PENDING
    delivery_attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "created": self.created.isoformat(),
            "expires": self.expires.isoformat(),
            "strategy": self.strategy,
            "payload": self.payload.to_dict(),
            "status": self.status,
            "delivery_attempts": self.delivery_attempts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedNotification:
        """Deserialize from storage."""
        return cls(
            id=data["id"],
            created=dt_util.parse_datetime(data["created"]) or dt_util.utcnow(),
            expires=dt_util.parse_datetime(data["expires"]) or dt_util.utcnow(),
            strategy=data["strategy"],
            payload=NotificationPayload.from_dict(data["payload"]),
            status=data.get("status", QUEUE_STATUS_PENDING),
            delivery_attempts=data.get("delivery_attempts", 0),
        )


@dataclass(slots=True)
class SmartNotifyConfig:
    """Runtime configuration for Smart Notify."""

    persons: list[str]
    person_services: dict[str, list[str]]
    default_strategy: str = DEFAULT_STRATEGY
    default_tolerance: int = DEFAULT_TOLERANCE
    default_expire_after: str = DEFAULT_EXPIRE_AFTER
    log_level: str = "info"
    arrival_debounce_seconds: int = DEFAULT_ARRIVAL_DEBOUNCE_SECONDS

    @classmethod
    def from_entry_data(cls, data: Mapping[str, Any]) -> SmartNotifyConfig:
        """Build configuration from a config entry."""
        return cls(
            persons=list(data.get("persons", [])),
            person_services={
                key: list(value)
                for key, value in data.get("person_services", {}).items()
            },
            default_strategy=data.get("default_strategy", DEFAULT_STRATEGY),
            default_tolerance=int(data.get("default_tolerance", DEFAULT_TOLERANCE)),
            default_expire_after=data.get("default_expire_after", DEFAULT_EXPIRE_AFTER),
            log_level=data.get("log_level", "info"),
            arrival_debounce_seconds=int(
                data.get("arrival_debounce_seconds", DEFAULT_ARRIVAL_DEBOUNCE_SECONDS)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration."""
        return {
            "persons": self.persons,
            "person_services": self.person_services,
            "default_strategy": self.default_strategy,
            "default_tolerance": self.default_tolerance,
            "default_expire_after": self.default_expire_after,
            "log_level": self.log_level,
            "arrival_debounce_seconds": self.arrival_debounce_seconds,
        }


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    """Record of a delivery attempt."""

    notification_id: str
    recipients: list[str]
    services: list[str]
    delivered_at: datetime
    success: bool
    error: str | None = None
