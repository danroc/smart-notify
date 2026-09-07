"""Build notify service payloads from notification data."""

from __future__ import annotations

import copy
from typing import Any

from ..const import LEVEL_NOTIFY_DATA
from ..models import NotificationPayload
from ..util import compact_dict


def has_rich_notify_data(data: dict[str, Any]) -> bool:
    """Return whether the notify call includes a non-empty data block."""
    return bool(data.get("data"))


def build_send_message_data(data: dict[str, Any]) -> dict[str, Any]:
    """Build the payload used by ``notify.send_message``."""
    return {"message": data["message"]} | compact_dict([
        ("title", data.get("title")),
    ])


def build_notify_data(payload: NotificationPayload) -> dict[str, Any]:
    """Build notify service data from a payload."""
    # Copy so callers never receive the module-level constant itself.
    level_data = copy.deepcopy(LEVEL_NOTIFY_DATA[payload.level])

    notify_data = level_data | compact_dict([
        ("group", payload.group),
        ("image", payload.image),
        # iOS reads the tap target from `url`, Android from `clickAction`.
        ("url", payload.url),
        ("clickAction", payload.url),
        ("tag", payload.tag),
        ("actions", payload.actions),
    ])

    return {"message": payload.message} | compact_dict([
        ("title", payload.title),
        ("data", notify_data),
    ])
