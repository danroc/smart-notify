"""Build notification payloads from service call data."""

from __future__ import annotations

from typing import Any

from homeassistant.util import dt as dt_util

from ..const import (
    ATTR_ACTIONS,
    ATTR_EXPIRE_AFTER,
    ATTR_GROUP,
    ATTR_IMAGE,
    ATTR_LEVEL,
    ATTR_MESSAGE,
    ATTR_PERSONS,
    ATTR_STRATEGY,
    ATTR_TAG,
    ATTR_TITLE,
    ATTR_TOLERANCE,
    ATTR_URL,
    DEFAULT_LEVEL,
)
from ..models import NotificationPayload, SmartNotifyConfig
from ..util import generate_id, parse_expire_after


def build_payload(
    config: SmartNotifyConfig,
    service_data: dict[str, Any],
) -> NotificationPayload:
    """Build a notification payload from service data."""
    now = dt_util.utcnow()
    expire_after = service_data.get(
        ATTR_EXPIRE_AFTER,
        config.default_expire_after,
    )
    strategy = service_data.get(ATTR_STRATEGY, config.default_strategy)
    return NotificationPayload(
        id=generate_id(),
        title=service_data.get(ATTR_TITLE),
        message=service_data[ATTR_MESSAGE],
        strategy=strategy,
        tag=service_data.get(ATTR_TAG),
        level=service_data.get(ATTR_LEVEL, DEFAULT_LEVEL),
        group=service_data.get(ATTR_GROUP),
        image=service_data.get(ATTR_IMAGE),
        url=service_data.get(ATTR_URL),
        actions=service_data.get(ATTR_ACTIONS),
        created=now,
        expires=parse_expire_after(str(expire_after), now),
        tolerance=service_data.get(ATTR_TOLERANCE, config.default_tolerance),
        persons=service_data.get(ATTR_PERSONS),
    )
