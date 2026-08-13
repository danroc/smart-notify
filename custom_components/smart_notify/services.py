"""Service registration for Smart Notify."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_CHANNELS,
    ATTR_DATA,
    ATTR_EXPIRE_AFTER,
    ATTR_MESSAGE,
    ATTR_METADATA,
    ATTR_PERSONS,
    ATTR_PRIORITY,
    ATTR_QUEUE_IF_NO_CANDIDATE,
    ATTR_STRATEGY,
    ATTR_TAG,
    ATTR_TITLE,
    ATTR_TOLERANCE,
    DEFAULT_PRIORITY,
    DEFAULT_QUEUE_IF_NO_CANDIDATE,
    DOMAIN,
    LOGGER_NAME,
    SERVICE_SEND,
    STRATEGY_CHOICES,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from .coordinator import SmartNotifyCoordinator

_LOGGER = logging.getLogger(LOGGER_NAME)

SERVICE_SEND_SCHEMA = vol.Schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE): cv.string,
    vol.Optional(ATTR_STRATEGY): vol.In(STRATEGY_CHOICES),
    vol.Optional(ATTR_TOLERANCE): cv.positive_int,
    vol.Optional(
        ATTR_QUEUE_IF_NO_CANDIDATE, default=DEFAULT_QUEUE_IF_NO_CANDIDATE
    ): cv.boolean,
    vol.Optional(ATTR_EXPIRE_AFTER): cv.string,
    vol.Optional(ATTR_PRIORITY, default=DEFAULT_PRIORITY): cv.string,
    vol.Optional(ATTR_TAG): cv.string,
    vol.Optional(ATTR_DATA): dict,
    vol.Optional(ATTR_CHANNELS): [cv.string],
    vol.Optional(ATTR_METADATA): dict,
    vol.Optional(ATTR_PERSONS): vol.All(
        cv.ensure_list,
        [vol.All(cv.entity_id, cv.entity_domain("person"))],
        vol.Length(min=1),
    ),
})


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
