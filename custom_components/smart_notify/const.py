"""Constants for the Smart Notify integration."""

from __future__ import annotations

from logging import DEBUG, INFO, WARNING
from typing import Any, Final

# Integration identity used by Home Assistant and the component logger.
DOMAIN: Final = "smart_notify"
LOGGER_NAME: Final = "custom_components.smart_notify"

# Home Assistant Store file version. Bump only when the on-disk Store wrapper changes.
STORAGE_VERSION: Final = 2
STORAGE_KEY: Final = "smart_notify"

# Queue payload schema version stored in JSON data.
# Bump when queue item shape changes.
QUEUE_SCHEMA_VERSION: Final = 1

# Config-entry / options keys persisted by the config flow.
CONF_PERSONS: Final = "persons"
CONF_PERSON_SERVICES: Final = "person_services"
CONF_DEFAULT_STRATEGY: Final = "default_strategy"
CONF_DEFAULT_TOLERANCE: Final = "default_tolerance"
CONF_DEFAULT_EXPIRE_AFTER: Final = "default_expire_after"
CONF_LOG_LEVEL: Final = "log_level"
CONF_ARRIVAL_DEBOUNCE_SECONDS: Final = "arrival_debounce_seconds"
CONF_DEPARTURE_DEBOUNCE_SECONDS: Final = "departure_debounce_seconds"

# Registered Home Assistant service name.
SERVICE_SEND: Final = "send"

# `smart_notify.send` service data keys.
ATTR_TITLE: Final = "title"
ATTR_MESSAGE: Final = "message"
ATTR_STRATEGY: Final = "strategy"
ATTR_TOLERANCE: Final = "tolerance"
ATTR_EXPIRE_AFTER: Final = "expire_after"
ATTR_TAG: Final = "tag"
ATTR_ACTIONS: Final = "actions"
ATTR_LEVEL: Final = "level"
ATTR_GROUP: Final = "group"
ATTR_IMAGE: Final = "image"
ATTR_URL: Final = "url"
ATTR_PERSONS: Final = "persons"

# Urgency levels passed to notify payloads and the service schema.
LEVEL_SILENT: Final = "silent"
LEVEL_NORMAL: Final = "normal"
LEVEL_IMPORTANT: Final = "important"
LEVEL_CRITICAL: Final = "critical"
DEFAULT_LEVEL: Final = LEVEL_NORMAL

# Notify data merged in per level. `push` is read by iOS only, `priority` and
# `ttl` by Android only. Android channel `importance` is deliberately never set:
# it is write-once per channel, so applying it to the shared default channel
# would permanently change the urgency of unrelated notifications on the device.
LEVEL_NOTIFY_DATA: Final[dict[str, dict[str, Any]]] = {
    LEVEL_SILENT: {
        "push": {"interruption-level": "passive"},
    },
    LEVEL_NORMAL: {},
    LEVEL_IMPORTANT: {
        "priority": "high",
        "ttl": 0,
        "push": {"interruption-level": "time-sensitive"},
    },
    LEVEL_CRITICAL: {
        "priority": "high",
        "ttl": 0,
        "push": {"interruption-level": "critical"},
    },
}

LEVEL_CHOICES: Final = list(LEVEL_NOTIFY_DATA)
LEVEL_LABELS: Final = {
    LEVEL_SILENT: "Silent",
    LEVEL_NORMAL: "Normal",
    LEVEL_IMPORTANT: "Important",
    LEVEL_CRITICAL: "Critical",
}

# Fallback option values when a config entry has not overridden them.
DEFAULT_STRATEGY: Final = "closest"
DEFAULT_TOLERANCE: Final = 500
DEFAULT_EXPIRE_AFTER: Final = "4h"
DEFAULT_ARRIVAL_DEBOUNCE_SECONDS: Final = 30
DEFAULT_DEPARTURE_DEBOUNCE_SECONDS: Final = 30

# Lifecycle states stored on queued notifications.
QUEUE_STATUS_PENDING: Final = "pending"
QUEUE_STATUS_DELIVERED: Final = "delivered"
QUEUE_STATUS_EXPIRED: Final = "expired"
QUEUE_STATUS_FAILED: Final = "failed"

# Domain events fired as notifications move through the queue.
EVENT_SENT: Final = "smart_notify_sent"
EVENT_QUEUED: Final = "smart_notify_queued"
EVENT_DELIVERED: Final = "smart_notify_delivered"
EVENT_EXPIRED: Final = "smart_notify_expired"
EVENT_FAILED: Final = "smart_notify_failed"

# Sensor entity unique-id suffixes.
SENSOR_PENDING: Final = "pending"
SENSOR_DELIVERED_TODAY: Final = "delivered_today"
SENSOR_FAILED_TODAY: Final = "failed_today"

# Person/device_tracker states treated as "at home".
HOME_STATES: Final = frozenset({"home"})

# Logger verbosity offered in options, mapped to the stdlib logging levels.
LOG_LEVELS: Final = {
    "debug": DEBUG,
    "info": INFO,
    "warning": WARNING,
}
DEFAULT_LOG_LEVEL: Final = "info"

# Delivery strategies selectable per notification or as the entry default.
STRATEGY_DIRECT: Final = "direct"
STRATEGY_HOME: Final = "home"
STRATEGY_AWAY: Final = "away"
STRATEGY_CLOSEST: Final = "closest"
STRATEGY_ARRIVAL: Final = "arrival"
STRATEGY_DEPARTURE: Final = "departure"

STRATEGY_CHOICES: Final = [
    STRATEGY_DIRECT,
    STRATEGY_HOME,
    STRATEGY_AWAY,
    STRATEGY_CLOSEST,
    STRATEGY_ARRIVAL,
    STRATEGY_DEPARTURE,
]
STRATEGY_LABELS: Final = {
    STRATEGY_DIRECT: "Direct",
    STRATEGY_HOME: "Home",
    STRATEGY_AWAY: "Away",
    STRATEGY_CLOSEST: "Closest",
    STRATEGY_ARRIVAL: "Arrival",
    STRATEGY_DEPARTURE: "Departure",
}

# Strategies that hold the notification until a later condition is met.
STRATEGIES_QUEUE_BY_DEFAULT: Final = frozenset({
    STRATEGY_ARRIVAL,
    STRATEGY_CLOSEST,
    STRATEGY_DEPARTURE,
})

# Platforms this integration sets up besides the notify service.
PLATFORMS: Final = ["sensor"]
