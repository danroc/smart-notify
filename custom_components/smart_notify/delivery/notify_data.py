"""Build notify service payloads from notification data."""

from __future__ import annotations

from typing import Any

from ..const import LEVEL_NOTIFY_DATA
from ..models import NotificationPayload


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
    data: dict[str, Any] = {"message": payload.message}
    if payload.title:
        data["title"] = payload.title

    notify_data: dict[str, Any] = {
        key: value
        for key, value in (
            ("group", payload.group),
            ("image", payload.image),
            # iOS reads the tap target from `url`, Android from `clickAction`.
            ("url", payload.url),
            ("clickAction", payload.url),
            ("tag", payload.tag),
        )
        if value
    }
    if payload.actions:
        notify_data["actions"] = payload.actions
    level_data = LEVEL_NOTIFY_DATA[payload.level]
    notify_data.update(level_data)
    if push := level_data.get("push"):
        # Copy so callers never receive the module-level constant itself.
        notify_data["push"] = dict(push)
    if notify_data:
        data["data"] = notify_data
    return data
