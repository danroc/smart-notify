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
        """Map recipients to configured notify targets (entities or legacy services)."""
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
                    await self._async_call_notify(service, domain, service_name, data)
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

    async def _async_call_notify(
        self,
        target: str,
        domain: str,
        service_name: str,
        data: dict[str, Any],
    ) -> None:
        """Call a legacy notify service or notify.send_message for an entity."""
        if self._hass.services.has_service(domain, service_name):
            await self._hass.services.async_call(
                domain,
                service_name,
                data,
                blocking=True,
            )
            return

        if domain == "notify" and self._hass.states.get(target) is not None:
            send_data: dict[str, Any] = {"message": data["message"]}
            if "title" in data:
                send_data["title"] = data["title"]
            if "data" in data:
                _LOGGER.warning(
                    "Ignoring notify data for entity %s; use a legacy notify "
                    "service for rich payloads",
                    target,
                )
            await self._hass.services.async_call(
                "notify",
                "send_message",
                send_data,
                target={"entity_id": target},
                blocking=True,
            )
            return

        msg = f"Action {target} not found"
        raise ValueError(msg)

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
