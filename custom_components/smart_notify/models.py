"""Data models for Smart Notify."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
    DEFAULT_EXPIRE_AFTER,
    DEFAULT_LEVEL,
    DEFAULT_STRATEGY,
    DEFAULT_TOLERANCE,
    LEVEL_CHOICES,
    QUEUE_STATUS_PENDING,
)


@dataclass(frozen=True, slots=True)
class NotificationPayload:
    """Immutable notification payload."""

    id: str
    title: str | None
    message: str
    strategy: str
    tag: str | None
    level: str
    group: str | None
    image: str | None
    url: str | None
    created: datetime
    expires: datetime
    tolerance: int | None = None
    persons: list[str] | None = None
    actions: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "strategy": self.strategy,
            "tag": self.tag,
            "level": self.level,
            "group": self.group,
            "image": self.image,
            "url": self.url,
            "created": self.created.isoformat(),
            "expires": self.expires.isoformat(),
            "tolerance": self.tolerance,
            "persons": self.persons,
            "actions": self.actions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotificationPayload:
        """Deserialize from storage."""
        strategy = data["strategy"]
        legacy = data.get("payload")
        legacy_payload = legacy if isinstance(legacy, dict) else {}

        level = data.get("level", DEFAULT_LEVEL)
        if level not in LEVEL_CHOICES:
            level = DEFAULT_LEVEL

        def _field(key: str) -> str | None:
            value = data.get(key)
            if value:
                return str(value)
            legacy_value = legacy_payload.get(key)
            if legacy_value:
                return str(legacy_value)
            return None

        return cls(
            id=data["id"],
            title=data.get("title"),
            message=data["message"],
            strategy=strategy,
            tag=_field("tag"),
            level=level,
            group=_field("group"),
            image=_field("image"),
            url=_field("url"),
            created=dt_util.parse_datetime(data["created"]) or dt_util.utcnow(),
            expires=dt_util.parse_datetime(data["expires"]) or dt_util.utcnow(),
            tolerance=data.get("tolerance"),
            persons=data.get("persons"),
            actions=data.get("actions") or legacy_payload.get("actions"),
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
        payload = NotificationPayload.from_dict(data["payload"])
        return cls(
            id=data["id"],
            created=dt_util.parse_datetime(data["created"]) or dt_util.utcnow(),
            expires=dt_util.parse_datetime(data["expires"]) or dt_util.utcnow(),
            strategy=payload.strategy,
            payload=payload,
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
