"""Voluptuous schema fields for integration default settings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from ..const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
    DEFAULT_EXPIRE_AFTER,
    DEFAULT_LOG_LEVEL,
    DEFAULT_STRATEGY,
    DEFAULT_TOLERANCE,
)
from .selectors import (
    arrival_debounce_selector,
    duration_selector,
    log_level_selector,
    strategy_selector,
    tolerance_selector,
)
from .validators import cv_duration


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
