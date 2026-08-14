"""Event helpers for Smart Notify."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback

from .const import (
    EVENT_DELIVERED,
    EVENT_EXPIRED,
    EVENT_FAILED,
    EVENT_QUEUED,
    EVENT_SENT,
)


@callback
def _fire(hass: HomeAssistant, event_type: str, data: dict[str, Any]) -> None:
    """Fire a Smart Notify event."""
    hass.bus.async_fire(event_type, data)


def fire_sent(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Fire smart_notify_sent."""
    _fire(hass, EVENT_SENT, data)


def fire_queued(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Fire smart_notify_queued."""
    _fire(hass, EVENT_QUEUED, data)


def fire_delivered(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Fire smart_notify_delivered."""
    _fire(hass, EVENT_DELIVERED, data)


def fire_expired(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Fire smart_notify_expired."""
    _fire(hass, EVENT_EXPIRED, data)


def fire_failed(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Fire smart_notify_failed."""
    _fire(hass, EVENT_FAILED, data)
