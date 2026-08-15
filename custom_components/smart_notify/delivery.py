"""Notification delivery management."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import DEFAULT_LEVEL, LEVEL_TO_INTERRUPTION, LOGGER_NAME
from .models import DeliveryRecord, NotificationPayload, SmartNotifyConfig

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

    async def deliver(
        self,
        payload: NotificationPayload,
        recipients: list[str],
    ) -> DeliveryRecord:
        """Deliver a notification to recipients."""
        service_map = self.services_for_recipients(recipients)
        services_used: list[str] = []
        errors: list[str] = []
        data = self._build_notify_data(payload)

        for recipient, services in service_map.items():
            for service in services:
                domain, _, service_name = service.partition(".")
                if not domain or not service_name:
                    errors.append(f"Invalid notify service: {service}")
                    continue
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
            await self._hass.services.async_call(
                domain,
                service_name,
                data,
                blocking=True,
            )
            return

        if domain == "notify" and self._hass.states.get(target) is not None:
            if self._has_rich_notify_data(data):
                legacy_service = self._resolve_legacy_mobile_app_service(target)
                if legacy_service is not None:
                    legacy_domain, legacy_service_name = legacy_service
                    await self._hass.services.async_call(
                        legacy_domain,
                        legacy_service_name,
                        data,
                        blocking=True,
                    )
                    return
                _LOGGER.warning(
                    "Dropping rich notify data for entity %s; could not resolve "
                    "legacy mobile_app service",
                    target,
                )
            send_data: dict[str, Any] = {"message": data["message"]}
            if "title" in data:
                send_data["title"] = data["title"]
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

    def _resolve_legacy_mobile_app_service(
        self,
        entity_id: str,
    ) -> tuple[str, str] | None:
        """Resolve a mobile_app notify entity to a legacy notify service."""
        registry = er.async_get(self._hass)
        entry = registry.async_get(entity_id)
        if entry is None or entry.platform != "mobile_app" or not entry.device_id:
            return None

        device_registry = dr.async_get(self._hass)
        device = device_registry.async_get(entry.device_id)
        if device is None:
            return None

        service_name = slugify(f"mobile_app_{device.name}")
        if not self._hass.services.has_service("notify", service_name):
            return None
        return ("notify", service_name)

    @staticmethod
    def _has_rich_notify_data(data: dict[str, Any]) -> bool:
        """Return whether the notify call includes a non-empty data block."""
        notify_data = data.get("data")
        return bool(notify_data)

    @staticmethod
    def _build_notify_data(payload: NotificationPayload) -> dict[str, Any]:
        """Build notify service data from a payload."""
        data: dict[str, Any] = {"message": payload.message}
        if payload.title:
            data["title"] = payload.title

        notify_data: dict[str, Any] = {
            key: value
            for key, value in (
                ("group", payload.group),
                ("image", payload.image),
                ("url", payload.url),
                ("tag", payload.tag),
            )
            if value
        }
        if payload.actions:
            notify_data["actions"] = payload.actions
        if payload.level != DEFAULT_LEVEL:
            notify_data["push"] = {
                "interruption-level": LEVEL_TO_INTERRUPTION[payload.level],
            }
        if notify_data:
            data["data"] = notify_data
        return data
