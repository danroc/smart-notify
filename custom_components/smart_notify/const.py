"""Constants for the Smart Notify integration."""

from __future__ import annotations

from logging import DEBUG, INFO, WARNING
from typing import Final

DOMAIN: Final = "smart_notify"
LOGGER_NAME: Final = "custom_components.smart_notify"

STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "smart_notify"

CONF_PERSONS: Final = "persons"
CONF_PERSON_SERVICES: Final = "person_services"
CONF_DEFAULT_STRATEGY: Final = "default_strategy"
CONF_DEFAULT_TOLERANCE: Final = "default_tolerance"
CONF_DEFAULT_EXPIRE_AFTER: Final = "default_expire_after"
CONF_LOG_LEVEL: Final = "log_level"
CONF_ARRIVAL_DEBOUNCE_SECONDS: Final = "arrival_debounce_seconds"

SERVICE_SEND: Final = "send"

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

DEFAULT_LEVEL: Final = "normal"
LEVEL_SILENT: Final = "silent"
LEVEL_NORMAL: Final = "normal"
LEVEL_CRITICAL: Final = "critical"
LEVEL_CHOICES: Final = [LEVEL_SILENT, LEVEL_NORMAL, LEVEL_CRITICAL]
# Normal omits push on the notify call (Companion default). Only non-normal levels
# are mapped when building notify data.
LEVEL_TO_INTERRUPTION: Final = {
    LEVEL_SILENT: "passive",
    LEVEL_CRITICAL: "critical",
}

DEFAULT_STRATEGY: Final = "closest"
DEFAULT_TOLERANCE: Final = 500
DEFAULT_EXPIRE_AFTER: Final = "4h"
DEFAULT_ARRIVAL_DEBOUNCE_SECONDS: Final = 30

QUEUE_STATUS_PENDING: Final = "pending"
QUEUE_STATUS_DELIVERED: Final = "delivered"
QUEUE_STATUS_EXPIRED: Final = "expired"
QUEUE_STATUS_FAILED: Final = "failed"

EVENT_SENT: Final = "smart_notify_sent"
EVENT_QUEUED: Final = "smart_notify_queued"
EVENT_DELIVERED: Final = "smart_notify_delivered"
EVENT_EXPIRED: Final = "smart_notify_expired"
EVENT_FAILED: Final = "smart_notify_failed"

SENSOR_PENDING: Final = "pending"
SENSOR_DELIVERED_TODAY: Final = "delivered_today"
SENSOR_FAILED_TODAY: Final = "failed_today"

HOME_STATES: Final = frozenset({"home"})

LOG_LEVELS: Final = {
    "debug": DEBUG,
    "info": INFO,
    "warning": WARNING,
}

STRATEGY_DIRECT: Final = "direct"
STRATEGY_HOME: Final = "home"
STRATEGY_AWAY: Final = "away"
STRATEGY_CLOSEST: Final = "closest"
STRATEGY_ARRIVAL: Final = "arrival"

STRATEGY_CHOICES: Final = [
    STRATEGY_DIRECT,
    STRATEGY_HOME,
    STRATEGY_AWAY,
    STRATEGY_CLOSEST,
    STRATEGY_ARRIVAL,
]
STRATEGY_LABELS: Final = {
    STRATEGY_DIRECT: "Direct",
    STRATEGY_HOME: "Home",
    STRATEGY_AWAY: "Away",
    STRATEGY_CLOSEST: "Closest",
    STRATEGY_ARRIVAL: "Arrival",
}

STRATEGIES_QUEUE_BY_DEFAULT: Final = frozenset({STRATEGY_ARRIVAL, STRATEGY_CLOSEST})

PLATFORMS: Final = ["sensor"]
