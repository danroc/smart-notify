"""Utility helpers for Smart Notify."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util
from homeassistant.util import location as location_util

from .const import LOG_LEVELS, LOGGER_NAME, STRATEGIES_QUEUE_BY_DEFAULT

_LOGGER = logging.getLogger(LOGGER_NAME)


def configure_logging(level_name: str) -> None:
    """Configure integration logger level."""
    level = LOG_LEVELS.get(level_name.lower(), logging.INFO)
    _LOGGER.setLevel(level)


def generate_id() -> str:
    """Generate a unique notification identifier."""
    return uuid.uuid4().hex


def parse_expire_after(value: str, reference: datetime | None = None) -> datetime:
    """Parse a duration string such as '2h' into an expiry datetime."""
    base = reference or dt_util.utcnow()
    duration = parse_duration(value)
    return base + duration


def parse_duration(value: str) -> timedelta:
    """Parse shorthand duration strings like 2h, 30m, 1d."""
    normalized = value.strip().lower()
    if not normalized:
        msg = "Duration cannot be empty"
        raise ValueError(msg)

    unit = normalized[-1]
    amount_text = normalized[:-1]
    if not amount_text.isdigit():
        msg = f"Invalid duration: {value}"
        raise ValueError(msg)

    amount = int(amount_text)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "d":
        return timedelta(days=amount)
    if unit == "s":
        return timedelta(seconds=amount)

    msg = f"Unsupported duration unit in: {value}"
    raise ValueError(msg)


def is_eligible_person(state: State | None) -> bool:
    """Return True when a person entity is eligible for routing."""
    return state is not None and state.state not in {STATE_UNAVAILABLE, STATE_UNKNOWN}


def distance_to_home_meters(hass: HomeAssistant, state: State) -> float | None:
    """Return distance from a person to home in meters using HA helpers."""
    latitude = state.attributes.get(ATTR_LATITUDE)
    longitude = state.attributes.get(ATTR_LONGITUDE)
    if latitude is None or longitude is None:
        return None
    return location_util.distance(
        float(latitude),
        float(longitude),
        hass.config.latitude,
        hass.config.longitude,
    )


def get_person_states(hass: HomeAssistant, person_ids: list[str]) -> list[State]:
    """Return states for configured person entities."""
    states: list[State] = []
    for person_id in person_ids:
        state = hass.states.get(person_id)
        if state is not None:
            states.append(state)
    return states


def strategy_queues_when_empty(strategy: str) -> bool:
    """Return whether an empty recipient set should queue for this strategy.

    Arrival waits until someone gets home. Closest waits until someone has a
    usable location. Other strategies are snapshots of who matches now.
    """
    return strategy in STRATEGIES_QUEUE_BY_DEFAULT


def build_service_params(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract strategy parameters from a service call."""
    return {key: value for key, value in payload.items() if value is not None}
