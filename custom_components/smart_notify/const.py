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
ATTR_QUEUE_IF_NO_CANDIDATE: Final = "queue_if_no_candidate"
ATTR_EXPIRE_AFTER: Final = "expire_after"
ATTR_PRIORITY: Final = "priority"
ATTR_TAG: Final = "tag"
ATTR_DATA: Final = "data"
ATTR_CHANNELS: Final = "channels"
ATTR_METADATA: Final = "metadata"

DEFAULT_STRATEGY: Final = "closest"
DEFAULT_TOLERANCE: Final = 500
DEFAULT_EXPIRE_AFTER: Final = "4h"
DEFAULT_PRIORITY: Final = "normal"
DEFAULT_QUEUE_IF_NO_CANDIDATE: Final = True
DEFAULT_ARRIVAL_DEBOUNCE_SECONDS: Final = 30

PRIORITY_NORMAL: Final = "normal"
PRIORITY_HIGH: Final = "high"
PRIORITY_LOW: Final = "low"

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

STRATEGY_EVERYONE: Final = "everyone"
STRATEGY_EVERYONE_HOME: Final = "everyone_home"
STRATEGY_EVERYONE_AWAY: Final = "everyone_away"
STRATEGY_CLOSEST: Final = "closest"
STRATEGY_FIRST_HOME: Final = "first_home"
STRATEGY_TEMPLATE: Final = "template"

STRATEGY_CHOICES: Final = [
    STRATEGY_EVERYONE,
    STRATEGY_EVERYONE_HOME,
    STRATEGY_EVERYONE_AWAY,
    STRATEGY_CLOSEST,
    STRATEGY_FIRST_HOME,
    STRATEGY_TEMPLATE,
]

PLATFORMS: Final = ["sensor"]
