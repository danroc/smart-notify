"""Coordinator for Smart Notify."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

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
    DEFAULT_LEVEL,
    DOMAIN,
    EVENT_DELIVERED,
    EVENT_EXPIRED,
    EVENT_FAILED,
    EVENT_QUEUED,
    EVENT_SENT,
    LOGGER_NAME,
)
from .delivery import DeliveryManager
from .events import fire_event
from .listeners import EventListener
from .models import DeliveryRecord, NotificationPayload, SmartNotifyConfig
from .queue import QueueManager
from .recipient import RecipientResolver
from .storage import SmartNotifyStorage
from .util import (
    generate_id,
    parse_expire_after,
    strategy_queues_when_empty,
)

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
        self._delivery = DeliveryManager(hass, config)
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
        await self._async_flush_queue(refresh=False)
        self._refresh_sensors()

    async def async_shutdown(self) -> None:
        """Shut down coordinator resources."""
        self._cancel_arrival_debounce()
        await self._listener.async_stop()

    def update_config(self, config: SmartNotifyConfig) -> None:
        """Update configuration."""
        self._config = config
        self._resolver = RecipientResolver(self.hass, config.persons)
        self._delivery.update_config(config)

    async def async_update_config(self, config: SmartNotifyConfig) -> None:
        """Update configuration and refresh person listeners."""
        self.update_config(config)
        await self._listener.async_update_persons(config.persons)

    async def async_send(self, service_data: dict[str, Any]) -> None:
        """Handle smart_notify.send."""
        payload = self._build_payload(service_data)
        recipients = self._resolver.resolve(
            payload.strategy, payload.strategy_params, payload.persons
        )

        self._fire_notification_event(
            EVENT_SENT,
            payload.id,
            strategy=payload.strategy,
            recipients=recipients,
        )

        try:
            if recipients:
                await self._async_deliver(payload, recipients)
                return

            if strategy_queues_when_empty(payload.strategy):
                queued = await self._queue.enqueue(payload)
                self._fire_notification_event(
                    EVENT_QUEUED,
                    queued.id,
                    strategy=queued.strategy,
                    expires=queued.expires.isoformat(),
                )
                _LOGGER.debug("No recipients, queued notification %s", queued.id)
                return

            _LOGGER.debug("No recipients and strategy does not queue")
        finally:
            self._refresh_sensors()

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

    def _cancel_arrival_debounce(self) -> None:
        """Cancel a pending arrival debounce timer."""
        if self._arrival_debounce_unsub is not None:
            self._arrival_debounce_unsub()
            self._arrival_debounce_unsub = None

    async def _async_flush_queue(self, *, refresh: bool = True) -> None:
        """Attempt delivery for all pending queued notifications."""
        pending = self._queue.list_pending()
        for item in pending:
            try:
                recipients = self._resolver.resolve(
                    item.strategy,
                    item.payload.strategy_params,
                    item.payload.persons,
                )
            except ValueError as err:
                await self._queue.remove(item.id)
                self._record_delivery_failure(item.id, str(err))
                continue
            if not recipients:
                continue
            record = await self._delivery.deliver(item.payload, recipients)
            await self._queue.remove(item.id)
            self._record_delivery_result(item.id, recipients, record)

        if refresh:
            self._refresh_sensors()

    async def _async_deliver(
        self,
        payload: NotificationPayload,
        recipients: list[str],
    ) -> None:
        """Deliver a notification immediately."""
        record = await self._delivery.deliver(payload, recipients)
        self._record_delivery_result(payload.id, recipients, record)

    def _record_delivery_result(
        self,
        notification_id: str,
        recipients: list[str],
        record: DeliveryRecord,
    ) -> None:
        """Update counters and fire events for a delivery attempt."""
        if record.success:
            self._increment_delivered()
            self._fire_notification_event(
                EVENT_DELIVERED,
                notification_id,
                recipients=recipients,
                services=record.services,
            )
            return

        self._record_delivery_failure(notification_id, record.error)

    def _record_delivery_failure(
        self,
        notification_id: str,
        error: str | None,
    ) -> None:
        """Update counters and fire events for a failed delivery."""
        self._increment_failed()
        self._fire_notification_event(EVENT_FAILED, notification_id, error=error)

    async def _async_expire_notifications(self) -> None:
        """Expire stale notifications."""
        expired = await self._queue.expire_stale()
        for item in expired:
            self._fire_notification_event(
                EVENT_EXPIRED,
                item.id,
                expired_at=dt_util.utcnow().isoformat(),
            )

    def _fire_notification_event(
        self,
        event_type: str,
        notification_id: str,
        **event_data: object,
    ) -> None:
        """Fire a Smart Notify event with the shared notification id."""
        fire_event(
            self.hass,
            event_type,
            {
                "notification_id": notification_id,
                **event_data,
            },
        )

    def _build_payload(self, service_data: dict[str, Any]) -> NotificationPayload:
        """Build a notification payload from service data."""
        now = dt_util.utcnow()
        expire_after = service_data.get(
            ATTR_EXPIRE_AFTER,
            self._config.default_expire_after,
        )
        strategy = service_data.get(ATTR_STRATEGY, self._config.default_strategy)
        return NotificationPayload(
            id=generate_id(),
            title=service_data.get(ATTR_TITLE),
            message=service_data[ATTR_MESSAGE],
            strategy=strategy,
            tag=service_data.get(ATTR_TAG),
            level=service_data.get(ATTR_LEVEL, DEFAULT_LEVEL),
            group=service_data.get(ATTR_GROUP),
            image=service_data.get(ATTR_IMAGE),
            url=service_data.get(ATTR_URL),
            actions=service_data.get(ATTR_ACTIONS),
            created=now,
            expires=parse_expire_after(str(expire_after), now),
            tolerance=service_data.get(ATTR_TOLERANCE, self._config.default_tolerance),
            persons=service_data.get(ATTR_PERSONS),
        )

    def _refresh_sensors(self) -> None:
        """Push updated sensor values to listeners."""
        self.async_set_updated_data(self._build_data())

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
