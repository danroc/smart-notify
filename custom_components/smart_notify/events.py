"""Event helpers for Smart Notify."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback


@callback
def fire_event(hass: HomeAssistant, event_type: str, data: dict[str, Any]) -> None:
    """Fire a Smart Notify event on the Home Assistant event bus."""
    hass.bus.async_fire(event_type, data)
