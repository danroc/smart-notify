"""Shared voluptuous schemas, selectors, and services.yaml catalog.

Send field definitions in ``SEND_FIELDS`` drive ``SERVICE_SEND_SCHEMA`` and
``render_services_yaml()``. After changing send fields, update the committed
``services.yaml`` from the catalog (``tests/test_schema.py`` asserts they match):

    uv run python -c "
from pathlib import Path
import yaml
from custom_components.smart_notify.schema import render_services_yaml
path = Path('custom_components/smart_notify/services.yaml')
path.write_text(yaml.safe_dump(render_services_yaml(), sort_keys=False))
"
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import (
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
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
    DEFAULT_EXPIRE_AFTER,
    DEFAULT_LEVEL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_STRATEGY,
    DEFAULT_TOLERANCE,
    LEVEL_CHOICES,
    LEVEL_LABELS,
    LOG_LEVELS,
    QUEUE_SCHEMA_VERSION,
    QUEUE_STATUS_DELIVERED,
    QUEUE_STATUS_EXPIRED,
    QUEUE_STATUS_FAILED,
    QUEUE_STATUS_PENDING,
    STRATEGY_CHOICES,
    STRATEGY_LABELS,
)
from .util import parse_duration


class _SerializableSelector(Protocol):
    """HA selector that can be serialized for services.yaml."""

    def serialize(self) -> dict[str, dict[str, Any]]:
        """Return the HA selector serialization payload for services.yaml."""
        ...


QUEUE_STATUS_CHOICES: tuple[str, ...] = (
    QUEUE_STATUS_PENDING,
    QUEUE_STATUS_DELIVERED,
    QUEUE_STATUS_EXPIRED,
    QUEUE_STATUS_FAILED,
)

SERVICE_SEND_NAME = "Send"
SERVICE_SEND_DESCRIPTION = (
    "Route a notification to the right people using presence and distance "
    "strategies, with optional queueing when nobody matches."
)


def cv_duration(value: object) -> str:
    """Validate duration shorthand such as 4h, 30m, or 1d."""
    if not isinstance(value, str):
        msg = "expected a duration string"
        raise vol.Invalid(msg)
    try:
        parse_duration(value)
    except ValueError as err:
        raise vol.Invalid(str(err)) from err
    return value


def _labeled_options(
    labels: Mapping[str, str],
) -> list[selector.SelectOptionDict]:
    """Return select options from a value-to-label mapping."""
    return [{"value": value, "label": label} for value, label in labels.items()]


def strategy_selector() -> selector.Selector[selector.SelectSelectorConfig]:
    """Return the strategy dropdown selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=_labeled_options(STRATEGY_LABELS)),
    )


def level_selector() -> selector.Selector[selector.SelectSelectorConfig]:
    """Return the notification level dropdown selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=_labeled_options(LEVEL_LABELS)),
    )


def log_level_selector() -> selector.Selector[selector.SelectSelectorConfig]:
    """Return the integration log-level dropdown selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=list(LOG_LEVELS)),
    )


def tolerance_selector() -> selector.Selector[selector.NumberSelectorConfig]:
    """Return the closest-strategy tolerance selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            step=50,
            mode=selector.NumberSelectorMode.BOX,
        ),
    )


def duration_selector() -> selector.Selector[selector.TextSelectorConfig]:
    """Return the expire-after duration text selector."""
    return selector.TextSelector()


def person_selector() -> selector.Selector[selector.EntitySelectorConfig]:
    """Return a multi-person entity selector."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="person", multiple=True),
    )


def notify_selector() -> selector.Selector[selector.EntitySelectorConfig]:
    """Return a multi-notify entity selector."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="notify", multiple=True),
    )


def arrival_debounce_selector() -> selector.Selector[selector.NumberSelectorConfig]:
    """Return the arrival debounce selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            max=600,
            step=5,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="seconds",
        ),
    )


ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("action"): cv.string,
        vol.Required("title"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

CV_STRATEGY = vol.In(STRATEGY_CHOICES)
CV_LEVEL = vol.In(LEVEL_CHOICES)
CV_TOLERANCE = cv.positive_int
CV_LOG_LEVEL = vol.In(LOG_LEVELS)
CV_ACTIONS = vol.All(cv.ensure_list, [ACTION_SCHEMA])
CV_PERSONS = vol.All(
    cv.ensure_list,
    [vol.All(cv.entity_id, cv.entity_domain("person"))],
    vol.Length(min=1),
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
        if isinstance(raw, Mapping):
            compacted[key] = _compact_selector_config(raw)
            continue
        compacted[key] = raw
    return compacted


def selector_to_yaml(sel: _SerializableSelector) -> dict[str, Any]:
    """Serialize a HA selector to the compact services.yaml form."""
    serialized = sel.serialize()["selector"]
    result: dict[str, Any] = {}
    for kind, config in serialized.items():
        compacted = (
            _compact_selector_config(config) if isinstance(config, Mapping) else {}
        )
        result[kind] = compacted or None
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

QUEUE_PAYLOAD_SCHEMA = vol.Schema(
    {
        vol.Required("id"): cv.string,
        vol.Required("message"): cv.string,
        vol.Required("strategy"): cv.string,
        vol.Required("created"): cv.string,
        vol.Required("expires"): cv.string,
        vol.Optional("title"): vol.Any(None, cv.string),
        vol.Optional("tag"): vol.Any(None, cv.string),
        vol.Optional("level", default=DEFAULT_LEVEL): CV_LEVEL,
        vol.Optional("group"): vol.Any(None, cv.string),
        vol.Optional("image"): vol.Any(None, cv.string),
        vol.Optional("url"): vol.Any(None, cv.string),
        vol.Optional("tolerance"): vol.Any(None, CV_TOLERANCE),
        vol.Optional("persons"): vol.Any(None, [cv.string]),
        vol.Optional("actions"): vol.Any(None, CV_ACTIONS),
    },
    extra=vol.ALLOW_EXTRA,
)

QUEUE_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required("id"): cv.string,
        vol.Required("payload"): QUEUE_PAYLOAD_SCHEMA,
        vol.Optional("status", default=QUEUE_STATUS_PENDING): vol.In(
            QUEUE_STATUS_CHOICES
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

STORAGE_SCHEMA = vol.Schema({
    vol.Required("schema_version"): vol.All(
        vol.Coerce(int),
        vol.In([QUEUE_SCHEMA_VERSION]),
    ),
    vol.Required("queue"): [QUEUE_ITEM_SCHEMA],
})


def defaults_schema_fields(
    defaults: Mapping[str, Any] | None = None,
) -> dict[vol.Marker, Any]:
    """Return schema fields for integration default settings."""
    data = defaults or {}
    return {
        vol.Required(
            CONF_DEFAULT_STRATEGY,
            default=data.get(CONF_DEFAULT_STRATEGY, DEFAULT_STRATEGY),
        ): strategy_selector(),
        vol.Required(
            CONF_DEFAULT_TOLERANCE,
            default=data.get(CONF_DEFAULT_TOLERANCE, DEFAULT_TOLERANCE),
        ): tolerance_selector(),
        vol.Required(
            CONF_DEFAULT_EXPIRE_AFTER,
            default=data.get(CONF_DEFAULT_EXPIRE_AFTER, DEFAULT_EXPIRE_AFTER),
        ): vol.All(duration_selector(), cv_duration),
        vol.Required(
            CONF_ARRIVAL_DEBOUNCE_SECONDS,
            default=data.get(
                CONF_ARRIVAL_DEBOUNCE_SECONDS, DEFAULT_ARRIVAL_DEBOUNCE_SECONDS
            ),
        ): arrival_debounce_selector(),
        vol.Required(
            CONF_LOG_LEVEL,
            default=data.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL),
        ): log_level_selector(),
    }
