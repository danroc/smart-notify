"""Notification delivery orchestration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..const import LOGGER_NAME
from ..models import DeliveryRecord, NotificationPayload, SmartNotifyConfig
from .mobile_app import resolve_legacy_mobile_app_service
from .notify_data import (
    build_notify_data,
    build_send_message_data,
    has_rich_notify_data,
)

_LOGGER = logging.getLogger(LOGGER_NAME)


class DeliveryManager:
    """Deliver notifications via configured notify services."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: SmartNotifyConfig,
    ) -> None:
        """Initialize delivery manager."""
        self._hass = hass
        self._config = config

    def update_config(self, config: SmartNotifyConfig) -> None:
        """Update runtime configuration."""
        self._config = config

    def services_for_recipients(self, recipients: list[str]) -> dict[str, list[str]]:
        """Map recipients to configured notify targets (entities or legacy services)."""
        mapping: dict[str, list[str]] = {}
        for recipient in recipients:
            services = self._config.person_services.get(recipient, [])
            if services:
                mapping[recipient] = list(services)
        return mapping

    @staticmethod
    def _split_service_target(service: str) -> tuple[str, str] | None:
        """Return ``(domain, service_name)`` when the target format is valid."""
        domain, _, service_name = service.partition(".")
        if not domain or not service_name:
            return None
        return domain, service_name

    async def deliver(
        self,
        payload: NotificationPayload,
        recipients: list[str],
    ) -> DeliveryRecord:
        """Deliver a notification to recipients."""
        service_map = self.services_for_recipients(recipients)
        services_used: list[str] = []
        errors: list[str] = []
        data = build_notify_data(payload)

        for recipient, services in service_map.items():
            for service in services:
                parsed = self._split_service_target(service)
                if parsed is None:
                    errors.append(f"Invalid notify service: {service}")
                    continue
                domain, service_name = parsed
                _LOGGER.debug(
                    "Delivering notification %s to %s via %s",
                    payload.id,
                    recipient,
                    service,
                )
                try:
                    await self._async_call_notify(service, domain, service_name, data)
                    services_used.append(service)
                except Exception as err:
                    message = f"Delivery to {service} failed: {err}"
                    _LOGGER.exception(message)
                    errors.append(message)

        success = bool(services_used)
        return DeliveryRecord(
            notification_id=payload.id,
            recipients=recipients,
            services=services_used,
            delivered_at=dt_util.utcnow(),
            success=success,
            error="; ".join(errors) if errors else None,
        )

    async def _async_call_notify(
        self,
        target: str,
        domain: str,
        service_name: str,
        data: dict[str, Any],
    ) -> None:
        """Call a legacy notify service or notify.send_message for an entity."""
        if self._hass.services.has_service(domain, service_name):
            await self._async_call_service(domain, service_name, data)
            return

        if domain == "notify" and self._hass.states.get(target) is not None:
            await self._async_call_notify_entity(target, data)
            return

        msg = f"Action {target} not found"
        raise ValueError(msg)

    async def _async_call_service(
        self,
        domain: str,
        service_name: str,
        data: dict[str, Any],
    ) -> None:
        """Call a Home Assistant service with blocking delivery."""
        await self._hass.services.async_call(
            domain,
            service_name,
            data,
            blocking=True,
        )

    async def _async_call_notify_entity(
        self,
        target: str,
        data: dict[str, Any],
    ) -> None:
        """Deliver to a notify entity with legacy fallback for rich payloads."""
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

        await self._hass.services.async_call(
            "notify",
            "send_message",
            build_send_message_data(data),
            target={"entity_id": target},
            blocking=True,
        )
