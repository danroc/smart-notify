"""Service registration for Smart Notify."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, LOGGER_NAME, SERVICE_SEND
from .coordinator import SmartNotifyCoordinator
from .schema import SERVICE_SEND_SCHEMA

_LOGGER = logging.getLogger(LOGGER_NAME)

__all__ = ["SERVICE_SEND_SCHEMA", "async_setup_services", "async_unload_services"]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Smart Notify services."""

    async def async_handle_send(call: ServiceCall) -> None:
        coordinator: SmartNotifyCoordinator = hass.data[DOMAIN]["coordinator"]
        _LOGGER.debug("Received smart_notify.send: %s", call.data)
        await coordinator.async_send(dict(call.data))

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND,
        async_handle_send,
        schema=SERVICE_SEND_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister Smart Notify services."""
    hass.services.async_remove(DOMAIN, SERVICE_SEND)
