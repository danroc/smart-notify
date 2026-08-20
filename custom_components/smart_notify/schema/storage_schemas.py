"""Voluptuous schemas for persisted queue and storage data."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from ..const import (
    DEFAULT_LEVEL,
    QUEUE_SCHEMA_VERSION,
    QUEUE_STATUS_DELIVERED,
    QUEUE_STATUS_EXPIRED,
    QUEUE_STATUS_FAILED,
    QUEUE_STATUS_PENDING,
)
from .validators import CV_ACTIONS, CV_LEVEL, CV_TOLERANCE

QUEUE_STATUS_CHOICES: tuple[str, ...] = (
    QUEUE_STATUS_PENDING,
    QUEUE_STATUS_DELIVERED,
    QUEUE_STATUS_EXPIRED,
    QUEUE_STATUS_FAILED,
)

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
