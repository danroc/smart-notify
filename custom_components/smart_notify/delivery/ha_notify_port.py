"""Home Assistant adapter for the notify port."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import LOGGER_NAME
from .mobile_app import resolve_legacy_mobile_app_service
from .notify_data import build_send_message_data, has_rich_notify_data

_LOGGER = logging.getLogger(LOGGER_NAME)


class HassNotifyPort:
    """Deliver notify data via Home Assistant notify services and entities."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the port."""
        self._hass = hass

    async def send(self, target: str, data: dict[str, Any]) -> None:
        """Deliver data to a legacy notify service or a notify entity."""
        domain, _, service_name = target.partition(".")
        if not domain or not service_name:
            msg = f"Invalid notify target: {target}"
            raise ValueError(msg)

        if self._hass.services.has_service(domain, service_name):
            await self._async_call_service(domain, service_name, data)
            return

        if domain == "notify" and self._hass.states.get(target) is not None:
            await self._async_send_to_entity(target, data)
            return

        msg = f"Action {target} not found"
        raise ValueError(msg)

    async def _async_call_service(
        self,
        domain: str,
        service_name: str,
        data: dict[str, Any],
        target: dict[str, Any] | None = None,
    ) -> None:
        """Call a Home Assistant service with blocking delivery."""
        await self._hass.services.async_call(
            domain,
            service_name,
            data,
            target=target,
            blocking=True,
        )

    async def _async_send_to_entity(
        self,
        target: str,
        data: dict[str, Any],
    ) -> None:
        """Deliver to a notify entity with legacy fallback for rich payloads."""
        # notify.send_message only accepts message/title; HA has no entity-based way to
        # deliver actions/critical alerts/images yet (home-assistant discussion #3684),
        # so the legacy per-device service is the only way to preserve rich data.
        if has_rich_notify_data(data):
            legacy_service = resolve_legacy_mobile_app_service(self._hass, target)
            if legacy_service is not None:
                legacy_domain, legacy_service_name = legacy_service
                await self._async_call_service(legacy_domain, legacy_service_name, data)
                return

            _LOGGER.warning(
                "Dropping rich notify data for entity %s; could not resolve "
                "legacy mobile_app service",
                target,
            )

        await self._async_call_service(
            "notify",
            "send_message",
            build_send_message_data(data),
            target={"entity_id": target},
        )
