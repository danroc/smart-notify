"""Data models for Smart Notify."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    CONF_PERSON_SERVICES,
    CONF_PERSONS,
    DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
    DEFAULT_EXPIRE_AFTER,
    DEFAULT_LEVEL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_STRATEGY,
    DEFAULT_TOLERANCE,
    LEVEL_CHOICES,
    QUEUE_STATUS_PENDING,
)


def _parse_stored_datetime(value: str | None) -> datetime:
    """Parse a stored ISO datetime, falling back to now."""
    if value is None:
        return dt_util.utcnow()
    return dt_util.parse_datetime(value) or dt_util.utcnow()


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

    @property
    def strategy_params(self) -> dict[str, Any]:
        """Parameters passed to the recipient strategy."""
        return {"tolerance": self.tolerance}

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

        level = data.get("level", DEFAULT_LEVEL)
        if level not in LEVEL_CHOICES:
            level = DEFAULT_LEVEL

        def _field(key: str) -> str | None:
            value = data.get(key)
            if value:
                return str(value)
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
            created=_parse_stored_datetime(data.get("created")),
            expires=_parse_stored_datetime(data.get("expires")),
            tolerance=data.get("tolerance"),
            persons=data.get("persons"),
            actions=data.get("actions"),
        )


@dataclass(slots=True)
class QueuedNotification:
    """A notification stored in the persistent queue."""

    id: str
    payload: NotificationPayload
    status: str = QUEUE_STATUS_PENDING

    @property
    def created(self) -> datetime:
        """When the notification was created."""
        return self.payload.created

    @property
    def expires(self) -> datetime:
        """When the notification expires."""
        return self.payload.expires

    @property
    def strategy(self) -> str:
        """Recipient selection strategy."""
        return self.payload.strategy

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "payload": self.payload.to_dict(),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedNotification:
        """Deserialize from storage."""
        payload = NotificationPayload.from_dict(data["payload"])
        return cls(
            id=data["id"],
            payload=payload,
            status=data.get("status", QUEUE_STATUS_PENDING),
        )


@dataclass(slots=True)
class SmartNotifyConfig:
    """Runtime configuration for Smart Notify."""

    persons: list[str]
    person_services: dict[str, list[str]]
    default_strategy: str = DEFAULT_STRATEGY
    default_tolerance: int = DEFAULT_TOLERANCE
    default_expire_after: str = DEFAULT_EXPIRE_AFTER
    log_level: str = DEFAULT_LOG_LEVEL
    arrival_debounce_seconds: int = DEFAULT_ARRIVAL_DEBOUNCE_SECONDS

    @classmethod
    def from_entry_data(cls, data: Mapping[str, Any]) -> SmartNotifyConfig:
        """Build configuration from a config entry."""
        return cls(
            persons=list(data.get(CONF_PERSONS, [])),
            person_services={
                key: list(value)
                for key, value in data.get(CONF_PERSON_SERVICES, {}).items()
            },
            default_strategy=data.get(CONF_DEFAULT_STRATEGY, DEFAULT_STRATEGY),
            default_tolerance=int(data.get(CONF_DEFAULT_TOLERANCE, DEFAULT_TOLERANCE)),
            default_expire_after=data.get(
                CONF_DEFAULT_EXPIRE_AFTER, DEFAULT_EXPIRE_AFTER
            ),
            log_level=data.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL),
            arrival_debounce_seconds=int(
                data.get(
                    CONF_ARRIVAL_DEBOUNCE_SECONDS, DEFAULT_ARRIVAL_DEBOUNCE_SECONDS
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration."""
        return {
            CONF_PERSONS: self.persons,
            CONF_PERSON_SERVICES: self.person_services,
            CONF_DEFAULT_STRATEGY: self.default_strategy,
            CONF_DEFAULT_TOLERANCE: self.default_tolerance,
            CONF_DEFAULT_EXPIRE_AFTER: self.default_expire_after,
            CONF_LOG_LEVEL: self.log_level,
            CONF_ARRIVAL_DEBOUNCE_SECONDS: self.arrival_debounce_seconds,
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
