"""Queued notification model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from ..const import QUEUE_STATUS_PENDING
from ..schema import QUEUE_ITEM_SCHEMA
from .payload import NotificationPayload


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
        """Deserialize and validate storage queue item data."""
        return cls.from_validated(QUEUE_ITEM_SCHEMA(data))

    @classmethod
    def from_validated(cls, item: Mapping[str, Any]) -> QueuedNotification:
        """Build from a dict already validated by ``QUEUE_ITEM_SCHEMA``."""
        data = cast("dict[str, Any]", item)
        return cls(
            id=data["id"],
            payload=NotificationPayload.from_validated(data["payload"]),
            status=data.get("status", QUEUE_STATUS_PENDING),
        )
