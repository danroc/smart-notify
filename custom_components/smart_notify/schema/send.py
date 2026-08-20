"""smart_notify.send field catalog, validation, and services.yaml generation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

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
)
from .selectors import (
    duration_selector,
    level_selector,
    person_selector,
    strategy_selector,
    tolerance_selector,
)
from .validators import (
    CV_ACTIONS,
    CV_LEVEL,
    CV_PERSONS,
    CV_STRATEGY,
    CV_TOLERANCE,
    cv_duration,
)


class _SerializableSelector(Protocol):
    """HA selector that can be serialized for services.yaml."""

    def serialize(self) -> dict[str, dict[str, Any]]:
        """Return the HA selector serialization payload for services.yaml."""
        ...


SERVICE_SEND_NAME = "Send"
SERVICE_SEND_DESCRIPTION = (
    "Route a notification to the right people using presence and distance "
    "strategies, with optional queueing when nobody matches."
)


@dataclass(frozen=True, slots=True)
class SendField:
    """One smart_notify.send field used for validation and services.yaml."""

    key: str
    required: bool
    validator: Any
    description: str
    selector: _SerializableSelector | None = None
    example: Any = None


SEND_FIELDS: tuple[SendField, ...] = (
    SendField(
        key=ATTR_MESSAGE,
        required=True,
        validator=cv.string,
        description="Notification body text delivered to the notify target.",
        selector=selector.TextSelector(),
        example="Washing machine finished.",
    ),
    SendField(
        key=ATTR_TITLE,
        required=False,
        validator=cv.string,
        description="Optional notification title shown on the device.",
        selector=selector.TextSelector(),
        example="Laundry",
    ),
    SendField(
        key=ATTR_STRATEGY,
        required=False,
        validator=CV_STRATEGY,
        description=(
            "Who should receive the notification. Defaults to the integration's "
            "configured default strategy. direct: everyone eligible; home: people "
            "at home now; away: people away now; closest: people within tolerance "
            "of the closest distance to home (queues when nobody has a usable "
            "location); arrival: people at home now, otherwise queue until "
            "someone arrives."
        ),
        selector=strategy_selector(),
        example="closest",
    ),
    SendField(
        key=ATTR_TOLERANCE,
        required=False,
        validator=CV_TOLERANCE,
        description=(
            "Distance in meters used by the closest strategy. Everyone whose "
            "distance to home is within this value of the closest person is "
            "notified. Defaults to the integration's configured default "
            "tolerance."
        ),
        selector=tolerance_selector(),
        example=500,
    ),
    SendField(
        key=ATTR_EXPIRE_AFTER,
        required=False,
        validator=cv_duration,
        description=(
            "How long a queued notification is kept before it expires. Duration "
            "shorthand such as 30m, 4h, or 1d. Defaults to the integration's "
            "configured default expiration."
        ),
        selector=duration_selector(),
        example="4h",
    ),
    SendField(
        key=ATTR_LEVEL,
        required=False,
        validator=CV_LEVEL,
        description=(
            "Notification urgency on mobile devices. silent: passive delivery; "
            "normal: standard alert; important: elevated alert (time-sensitive "
            "on iOS, high priority on Android); critical: time-critical alert "
            "that can break through focus modes."
        ),
        selector=level_selector(),
        example="normal",
    ),
    SendField(
        key=ATTR_TAG,
        required=False,
        validator=cv.string,
        description=(
            "Tag passed to the mobile app notify payload. A new notification "
            "with the same tag replaces the previous one. Ignored by iOS for "
            "critical notifications."
        ),
        selector=selector.TextSelector(),
        example="laundry",
    ),
    SendField(
        key=ATTR_GROUP,
        required=False,
        validator=cv.string,
        description=(
            "Group name for stacking notifications on the device. Ignored by "
            "iOS for critical notifications."
        ),
        selector=selector.TextSelector(),
        example="appliances",
    ),
    SendField(
        key=ATTR_IMAGE,
        required=False,
        validator=cv.string,
        description="Image URL shown in the notification.",
        selector=selector.TextSelector(),
        example="/local/laundry.jpg",
    ),
    SendField(
        key=ATTR_URL,
        required=False,
        validator=cv.string,
        description=(
            "URL opened when the notification is tapped. Accepts a relative "
            "path such as /lovelace/laundry or a full URL."
        ),
        selector=selector.TextSelector(),
        example="/lovelace/laundry",
    ),
    SendField(
        key=ATTR_ACTIONS,
        required=False,
        validator=CV_ACTIONS,
        description=(
            "Action buttons for the Companion app (long-press on iOS). Android "
            "shows at most 3 buttons, iOS around 10. Handled via "
            "mobile_app_notification_action automations."
        ),
        example=[{"action": "ACK", "title": "Got it"}],
    ),
    SendField(
        key=ATTR_PERSONS,
        required=False,
        validator=CV_PERSONS,
        description="Optional subset of configured person entities to consider.",
        selector=person_selector(),
    ),
)


def _send_voluptuous_schema(fields: Sequence[SendField]) -> vol.Schema:
    """Build a voluptuous schema from send field definitions."""
    schema_dict: dict[vol.Marker, Any] = {}
    for field in fields:
        marker: vol.Marker = (
            vol.Required(field.key) if field.required else vol.Optional(field.key)
        )
        schema_dict[marker] = field.validator
    return vol.Schema(schema_dict)


def _compact_selector_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Drop selector defaults so rendered yaml matches HA's usual shape."""
    compacted: dict[str, Any] = {}
    for key, raw in config.items():
        if raw is False or raw is None:
            continue
        if key == "domain" and isinstance(raw, list) and len(raw) == 1:
            compacted[key] = raw[0]
            continue
        if isinstance(raw, float) and raw.is_integer():
            compacted[key] = int(raw)
            continue
        compacted[key] = raw
    return compacted


def selector_to_yaml(sel: _SerializableSelector) -> dict[str, Any]:
    """Serialize a HA selector to the compact services.yaml form."""
    serialized = sel.serialize()["selector"]
    result: dict[str, Any] = {}
    for kind, config in serialized.items():
        result[kind] = _compact_selector_config(config) or None
    return result


def render_services_yaml() -> dict[str, Any]:
    """Return the services.yaml structure generated from SEND_FIELDS."""
    fields: dict[str, Any] = {}
    for field in SEND_FIELDS:
        entry: dict[str, Any] = {
            "required": field.required,
            "description": field.description,
        }
        if field.example is not None:
            entry["example"] = field.example
        if field.selector is not None:
            entry["selector"] = selector_to_yaml(field.selector)
        fields[field.key] = entry
    return {
        "send": {
            "name": SERVICE_SEND_NAME,
            "description": SERVICE_SEND_DESCRIPTION,
            "fields": fields,
        }
    }


SERVICE_SEND_SCHEMA = _send_voluptuous_schema(SEND_FIELDS)
