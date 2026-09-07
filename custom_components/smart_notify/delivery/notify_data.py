"""Build notify service payloads from notification data."""

from __future__ import annotations

import copy
from typing import Any

from ..const import LEVEL_NOTIFY_DATA
from ..models import NotificationPayload
from ..util import compact_dict


def has_rich_notify_data(data: dict[str, Any]) -> bool:
    """Return whether the notify call includes a non-empty data block."""
    notify_data = data.get("data")
    return bool(notify_data)


def build_send_message_data(data: dict[str, Any]) -> dict[str, Any]:
    """Build the payload used by ``notify.send_message``."""
    send_data: dict[str, Any] = {"message": data["message"]}
    if "title" in data:
        send_data["title"] = data["title"]
    return send_data


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

    data: dict[str, Any] = {"message": payload.message}
    data.update(
        compact_dict([
            ("title", payload.title),
            ("data", notify_data),
        ])
    )

    return data
