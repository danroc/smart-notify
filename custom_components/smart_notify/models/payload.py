"""Notification payload model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from homeassistant.util import dt as dt_util

from ..schema import QUEUE_PAYLOAD_SCHEMA


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
        """Deserialize and validate storage payload data."""
        return cls.from_validated(QUEUE_PAYLOAD_SCHEMA(data))

    @classmethod
    def from_validated(cls, validated: Mapping[str, Any]) -> NotificationPayload:
        """Build from a dict already validated by ``QUEUE_PAYLOAD_SCHEMA``."""
        data = cast("dict[str, Any]", validated)

        def _field(key: str) -> str | None:
            value = data.get(key)
            if value:
                return str(value)
            return None

        return cls(
            id=data["id"],
            title=data.get("title"),
            message=data["message"],
            strategy=data["strategy"],
            tag=_field("tag"),
            level=data["level"],
            group=_field("group"),
            image=_field("image"),
            url=_field("url"),
            created=_parse_stored_datetime(data.get("created")),
            expires=_parse_stored_datetime(data.get("expires")),
            tolerance=data.get("tolerance"),
            persons=data.get("persons"),
            actions=data.get("actions"),
        )
