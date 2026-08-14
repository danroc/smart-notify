"""Service registration for Smart Notify."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ACTIONS,
    ATTR_EXPIRE_AFTER,
    ATTR_GROUP,
    ATTR_IMAGE,
    ATTR_LEVEL,
    ATTR_MESSAGE,
    ATTR_PERSONS,
    ATTR_STRATEGY,
    ATTR_TAG,
    ATTR_TITLE,
    ATTR_TOLERANCE,
    ATTR_URL,
    DOMAIN,
    LEVEL_CHOICES,
    LOGGER_NAME,
    SERVICE_SEND,
    STRATEGY_CHOICES,
)
from .coordinator import SmartNotifyCoordinator

_LOGGER = logging.getLogger(LOGGER_NAME)

ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("action"): cv.string,
        vol.Required("title"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_SEND_SCHEMA = vol.Schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE): cv.string,
    vol.Optional(ATTR_STRATEGY): vol.In(STRATEGY_CHOICES),
    vol.Optional(ATTR_TOLERANCE): cv.positive_int,
    vol.Optional(ATTR_EXPIRE_AFTER): cv.string,
    vol.Optional(ATTR_TAG): cv.string,
    vol.Optional(ATTR_LEVEL): vol.In(LEVEL_CHOICES),
    vol.Optional(ATTR_GROUP): cv.string,
    vol.Optional(ATTR_IMAGE): cv.string,
    vol.Optional(ATTR_URL): cv.string,
    vol.Optional(ATTR_ACTIONS): vol.All(cv.ensure_list, [ACTION_SCHEMA]),
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
