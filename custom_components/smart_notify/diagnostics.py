"""Diagnostics support for Smart Notify."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    storage_data = coordinator.storage.as_dict()
    return {
        "config_entry": dict(entry.data),
        "options": dict(entry.options),
        "queue": storage_data.get("queue", []),
        "strategy_evaluation": coordinator.get_last_evaluation(),
        "pending_count": coordinator.pending_count(),
        "delivered_today": coordinator.delivered_today(),
        "failed_today": coordinator.failed_today(),
    }
