"""Notification delivery management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

from .const import LOGGER_NAME
from .models import DeliveryRecord, NotificationPayload, SmartNotifyConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .storage import SmartNotifyStorage

_LOGGER = logging.getLogger(LOGGER_NAME)


class DeliveryManager:
    """Deliver notifications via configured notify services."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: SmartNotifyConfig,
        storage: SmartNotifyStorage,
    ) -> None:
        """Initialize delivery manager."""
        self._hass = hass
        self._config = config
        self._storage = storage

    def update_config(self, config: SmartNotifyConfig) -> None:
        """Update runtime configuration."""
        self._config = config

    def services_for_recipients(self, recipients: list[str]) -> dict[str, list[str]]:
        """Map recipients to notify service entity IDs."""
        mapping: dict[str, list[str]] = {}
        for recipient in recipients:
            services = self._config.person_services.get(recipient, [])
            if services:
                mapping[recipient] = list(services)
        return mapping

    async def deliver(
        self,
        payload: NotificationPayload,
        recipients: list[str],
    ) -> DeliveryRecord:
        """Deliver a notification to recipients."""
        service_map = self.services_for_recipients(recipients)
        services_used: list[str] = []
        errors: list[str] = []

        for recipient, services in service_map.items():
            for service in services:
                domain, _, service_name = service.partition(".")
                if not domain or not service_name:
                    errors.append(f"Invalid notify service: {service}")
                    continue
                data = self._build_notify_data(payload)
                _LOGGER.debug(
                    "Delivering notification %s to %s via %s",
                    payload.id,
                    recipient,
                    service,
                )
                try:
                    await self._hass.services.async_call(
                        domain,
                        service_name,
                        data,
                        blocking=True,
                    )
                    services_used.append(service)
                except Exception as err:
                    message = f"Delivery to {service} failed: {err}"
                    _LOGGER.exception(message)
                    errors.append(message)

        success = bool(services_used)
        record = DeliveryRecord(
            notification_id=payload.id,
            recipients=recipients,
            services=services_used,
            delivered_at=dt_util.utcnow(),
            success=success,
            error="; ".join(errors) if errors else None,
        )
        self._storage.add_delivery({
            "notification_id": record.notification_id,
            "recipients": record.recipients,
            "services": record.services,
            "delivered_at": record.delivered_at.isoformat(),
            "success": record.success,
            "error": record.error,
        })
        if errors:
            self._storage.add_error({
                "notification_id": payload.id,
                "errors": errors,
                "timestamp": dt_util.utcnow().isoformat(),
            })
        await self._storage.async_save()
        return record

    @staticmethod
    def _build_notify_data(payload: NotificationPayload) -> dict[str, Any]:
        """Build notify service data from a payload."""
        data: dict[str, Any] = {"message": payload.message}
        if payload.title:
            data["title"] = payload.title
        if payload.payload:
            data["data"] = payload.payload
        if payload.tag:
            data["data"] = {**(data.get("data") or {}), "tag": payload.tag}
        return data
