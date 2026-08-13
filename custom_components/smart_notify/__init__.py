"""Smart Notify integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import (
    strategies as _strategies,  # ruff: ignore[unused-import]  # register strategies
)
from .const import DOMAIN, LOGGER_NAME, PLATFORMS
from .coordinator import SmartNotifyCoordinator
from .models import SmartNotifyConfig
from .services import async_setup_services, async_unload_services
from .storage import SmartNotifyStorage
from .util import configure_logging

_LOGGER = logging.getLogger(LOGGER_NAME)


async def async_setup(_hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Set up Smart Notify."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Notify from a config entry."""
    smart_config = SmartNotifyConfig.from_entry_data(entry.data)
    configure_logging(smart_config.log_level)

    storage = SmartNotifyStorage(hass)
    coordinator = SmartNotifyCoordinator(hass, smart_config, storage)
    await coordinator.async_setup()
    storage.set_configuration(smart_config)
    await storage.async_save()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["coordinator"] = coordinator
    hass.data[DOMAIN]["storage"] = storage

    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _LOGGER.info("Smart Notify initialized")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Smart Notify."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SmartNotifyCoordinator = hass.data[DOMAIN]["coordinator"]
        await coordinator.async_shutdown()
        await async_unload_services(hass)
        hass.data.pop(DOMAIN, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator: SmartNotifyCoordinator = hass.data[DOMAIN]["coordinator"]
    smart_config = SmartNotifyConfig.from_entry_data({**entry.data, **entry.options})
    await coordinator.async_update_config(smart_config)
    configure_logging(smart_config.log_level)
    await coordinator.storage.async_save()
