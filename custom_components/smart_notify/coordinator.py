"""Coordinator for Smart Notify."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER_NAME
from .delivery import DeliveryManager
from .events import fire_delivered, fire_expired, fire_failed, fire_queued, fire_sent
from .listeners import EventListener
from .models import NotificationPayload, SmartNotifyConfig
from .queue import QueueManager
from .recipient import RecipientResolver
from .util import (
    default_queue_if_no_candidate,
    generate_id,
    parse_expire_after,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.core import HomeAssistant, State

    from .storage import SmartNotifyStorage

_LOGGER = logging.getLogger(LOGGER_NAME)


class SmartNotifyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate recipient resolution, queueing, and delivery."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: SmartNotifyConfig,
        storage: SmartNotifyStorage,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self._config = config
        self._storage = storage
        self._resolver = RecipientResolver(hass, config.persons)
        self._queue = QueueManager(storage)
        self._delivery = DeliveryManager(hass, config, storage)
        self._listener = EventListener(hass, config.persons)
        self._delivered_today = 0
        self._failed_today = 0
        self._today = dt_util.utcnow().date()
        self._arrival_debounce_unsub: Callable[[], None] | None = None

    @property
    def config(self) -> SmartNotifyConfig:
        """Current configuration."""
        return self._config

    @property
    def queue_manager(self) -> QueueManager:
        """Queue manager."""
        return self._queue

    @property
    def resolver(self) -> RecipientResolver:
        """Recipient resolver."""
        return self._resolver

    @property
    def storage(self) -> SmartNotifyStorage:
        """Persistent storage."""
        return self._storage

    def pending_count(self) -> int:
        """Return pending queue count."""
        return self._queue.count_pending()

    def delivered_today(self) -> int:
        """Return deliveries completed today."""
        self._reset_daily_counters_if_needed()
        return self._delivered_today

    def failed_today(self) -> int:
        """Return failed deliveries today."""
        self._reset_daily_counters_if_needed()
        return self._failed_today

    async def async_setup(self) -> None:
        """Set up coordinator resources."""
        await self._storage.async_load()
        self._listener.set_arrival_callback(self._async_on_person_arrival)
        await self._listener.async_start()
        await self._async_expire_notifications()
        await self._async_flush_queue()
        self.async_set_updated_data(self._build_data())

    async def async_shutdown(self) -> None:
        """Shut down coordinator resources."""
        self._cancel_arrival_debounce()
        await self._listener.async_stop()

    def update_config(self, config: SmartNotifyConfig) -> None:
        """Update configuration."""
        self._config = config
        self._resolver = RecipientResolver(self.hass, config.persons)
        self._delivery.update_config(config)
        self._storage.set_configuration(config)

    async def async_update_config(self, config: SmartNotifyConfig) -> None:
        """Update configuration and refresh person listeners."""
        self.update_config(config)
        await self._listener.async_update_persons(config.persons)

    async def async_send(self, service_data: dict[str, Any]) -> None:
        """Handle smart_notify.send."""
        payload = self._build_payload(service_data)
        params = self._build_strategy_params_from_payload(payload)
        recipients = self._resolver.resolve(payload.strategy, params, payload.persons)

        fire_sent(
            self.hass,
            {
                "notification_id": payload.id,
                "strategy": payload.strategy,
                "recipients": recipients,
            },
        )

        if recipients:
            await self._async_deliver(payload, recipients)
            self.async_set_updated_data(self._build_data())
            return

        if payload.queue_if_no_candidate:
            queued = await self._queue.enqueue(payload)
            fire_queued(
                self.hass,
                {
                    "notification_id": queued.id,
                    "strategy": queued.strategy,
                    "expires": queued.expires.isoformat(),
                },
            )
            _LOGGER.debug("No recipients, queued notification %s", queued.id)
            self.async_set_updated_data(self._build_data())
            return

        _LOGGER.debug("No recipients and queue_if_no_candidate is false")
        self.async_set_updated_data(self._build_data())

    async def _async_on_person_arrival(
        self,
        entity_id: str,
        _old_state: State,
        _new_state: State,
    ) -> None:
        """Debounce queue flush when a person arrives home."""
        delay = self._config.arrival_debounce_seconds
        _LOGGER.debug(
            "Scheduling queue evaluation after arrival of %s (debounce %ss)",
            entity_id,
            delay,
        )
        self._cancel_arrival_debounce()

        @callback
        def _run_flush(_now: datetime) -> None:
            self._arrival_debounce_unsub = None
            self.hass.async_create_task(self._async_flush_after_arrival())

        self._arrival_debounce_unsub = async_call_later(self.hass, delay, _run_flush)

    async def _async_flush_after_arrival(self) -> None:
        """Expire and flush the queue after the arrival debounce window."""
        await self._async_expire_notifications()
        await self._async_flush_queue()
        self.async_set_updated_data(self._build_data())

    def _cancel_arrival_debounce(self) -> None:
        """Cancel a pending arrival debounce timer."""
        if self._arrival_debounce_unsub is not None:
            self._arrival_debounce_unsub()
            self._arrival_debounce_unsub = None

    async def _async_flush_queue(self) -> None:
        """Attempt delivery for all pending queued notifications."""
        pending = self._queue.list_pending()
        for item in pending:
            params = self._build_strategy_params_from_payload(item.payload)
            try:
                recipients = self._resolver.resolve(
                    item.strategy, params, item.payload.persons
                )
            except ValueError as err:
                await self._queue.mark_failed(item.id)
                self._increment_failed()
                fire_failed(
                    self.hass,
                    {
                        "notification_id": item.id,
                        "error": str(err),
                    },
                )
                continue
            if not recipients:
                continue
            await self._queue.mark_attempt(item.id)
            record = await self._delivery.deliver(item.payload, recipients)
            if record.success:
                await self._queue.remove(item.id)
                self._increment_delivered()
                fire_delivered(
                    self.hass,
                    {
                        "notification_id": item.id,
                        "recipients": recipients,
                        "services": record.services,
                    },
                )
            else:
                await self._queue.mark_failed(item.id)
                self._increment_failed()
                fire_failed(
                    self.hass,
                    {
                        "notification_id": item.id,
                        "error": record.error,
                    },
                )

        self.async_set_updated_data(self._build_data())

    async def _async_deliver(
        self,
        payload: NotificationPayload,
        recipients: list[str],
    ) -> None:
        """Deliver a notification immediately."""
        record = await self._delivery.deliver(payload, recipients)
        if record.success:
            self._increment_delivered()
            fire_delivered(
                self.hass,
                {
                    "notification_id": payload.id,
                    "recipients": recipients,
                    "services": record.services,
                },
            )
        else:
            self._increment_failed()
            fire_failed(
                self.hass,
                {
                    "notification_id": payload.id,
                    "error": record.error,
                },
            )

    async def _async_expire_notifications(self) -> None:
        """Expire stale notifications."""
        expired = await self._queue.expire_stale()
        for item in expired:
            fire_expired(
                self.hass,
                {
                    "notification_id": item.id,
                    "expired_at": dt_util.utcnow().isoformat(),
                },
            )

    def _build_payload(self, service_data: dict[str, Any]) -> NotificationPayload:
        """Build a notification payload from service data."""
        now = dt_util.utcnow()
        expire_after = service_data.get(
            "expire_after",
            self._config.default_expire_after,
        )
        strategy = service_data.get("strategy", self._config.default_strategy)
        queue_if_no_candidate = service_data.get("queue_if_no_candidate")
        if queue_if_no_candidate is None:
            queue_if_no_candidate = default_queue_if_no_candidate(strategy)
        return NotificationPayload(
            id=generate_id(),
            title=service_data.get("title"),
            message=service_data["message"],
            strategy=strategy,
            priority=service_data.get("priority", "normal"),
            tag=service_data.get("tag"),
            payload=service_data.get("data", {}),
            created=now,
            expires=parse_expire_after(str(expire_after), now),
            metadata=service_data.get("metadata", {}),
            tolerance=service_data.get("tolerance", self._config.default_tolerance),
            queue_if_no_candidate=queue_if_no_candidate,
            channels=service_data.get("channels"),
            persons=service_data.get("persons"),
        )

    @staticmethod
    def _build_strategy_params_from_payload(
        payload: NotificationPayload,
    ) -> dict[str, Any]:
        """Build strategy parameters from a stored payload."""
        return {
            "tolerance": payload.tolerance,
        }

    def _increment_delivered(self) -> None:
        """Increment delivered counter."""
        self._reset_daily_counters_if_needed()
        self._delivered_today += 1

    def _increment_failed(self) -> None:
        """Increment failed counter."""
        self._reset_daily_counters_if_needed()
        self._failed_today += 1

    def _reset_daily_counters_if_needed(self) -> None:
        """Reset daily counters at UTC day boundary."""
        today = dt_util.utcnow().date()
        if today != self._today:
            self._today = today
            self._delivered_today = 0
            self._failed_today = 0

    def get_last_evaluation(self) -> dict[str, Any]:
        """Return diagnostics about the latest strategy evaluation."""
        pending = self._queue.list_pending()
        return {
            "pending": [item.to_dict() for item in pending],
            "configured_persons": self._config.persons,
        }

    def _build_data(self) -> dict[str, Any]:
        """Build coordinator data for entity updates."""
        return {
            "pending": self.pending_count(),
            "delivered_today": self.delivered_today(),
            "failed_today": self.failed_today(),
        }
