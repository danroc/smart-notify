"""Notification delivery orchestration."""

from __future__ import annotations

import logging

from homeassistant.util import dt as dt_util

from ..const import LOGGER_NAME
from ..models import DeliveryRecord, NotificationPayload, SmartNotifyConfig
from .notify_data import build_notify_data
from .port import NotifyPort

_LOGGER = logging.getLogger(LOGGER_NAME)


class DeliveryManager:
    """Deliver notifications via configured notify services."""

    def __init__(
        self,
        notify_port: NotifyPort,
        config: SmartNotifyConfig,
    ) -> None:
        """Initialize delivery manager."""
        self._notify_port = notify_port
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
        data = build_notify_data(payload)

        for recipient, services in service_map.items():
            for service in services:
                _LOGGER.debug(
                    "Delivering notification %s to %s via %s",
                    payload.id,
                    recipient,
                    service,
                )

                try:
                    await self._notify_port.send(service, data)
                    services_used.append(service)
                except Exception as err:
                    message = f"Delivery to {service} failed: {err}"
                    _LOGGER.exception(message)
                    errors.append(message)

        return DeliveryRecord(
            notification_id=payload.id,
            recipients=recipients,
            services=services_used,
            delivered_at=dt_util.utcnow(),
            success=bool(services_used),
            error="; ".join(errors) if errors else None,
        )
