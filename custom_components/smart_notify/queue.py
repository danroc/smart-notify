"""Persistent notification queue management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from .const import LOGGER_NAME, QUEUE_STATUS_EXPIRED, QUEUE_STATUS_PENDING
from .models import NotificationPayload, QueuedNotification
from .util import generate_id

if TYPE_CHECKING:
    from datetime import datetime

    from .storage import SmartNotifyStorage

_LOGGER = logging.getLogger(LOGGER_NAME)


class QueueManager:
    """Manage the persistent notification queue."""

    def __init__(self, storage: SmartNotifyStorage) -> None:
        """Initialize queue manager."""
        self._storage = storage

    def list_pending(self) -> list[QueuedNotification]:
        """Return pending notifications."""
        return [
            item
            for item in self._storage.get_queue()
            if item.status == QUEUE_STATUS_PENDING
        ]

    def count_pending(self) -> int:
        """Return number of pending notifications."""
        return len(self.list_pending())

    async def enqueue(self, payload: NotificationPayload) -> QueuedNotification:
        """Add a notification to the queue."""
        queued = QueuedNotification(
            id=payload.id or generate_id(),
            created=payload.created,
            expires=payload.expires,
            strategy=payload.strategy,
            payload=payload,
            status=QUEUE_STATUS_PENDING,
            delivery_attempts=0,
        )
        queue = self._storage.get_queue()
        queue.append(queued)
        self._storage.set_queue(queue)
        await self._storage.async_save()
        _LOGGER.debug("Queued notification %s", queued.id)
        return queued

    async def remove(self, notification_id: str) -> None:
        """Remove a notification from the queue."""
        queue = [
            item for item in self._storage.get_queue() if item.id != notification_id
        ]
        self._storage.set_queue(queue)
        await self._storage.async_save()
        _LOGGER.debug("Removed notification %s from queue", notification_id)

    async def mark_attempt(self, notification_id: str) -> None:
        """Increment delivery attempts for a queued notification."""
        queue = self._storage.get_queue()
        updated: list[QueuedNotification] = []
        for item in queue:
            if item.id == notification_id:
                item.delivery_attempts += 1
            updated.append(item)
        self._storage.set_queue(updated)
        await self._storage.async_save()

    async def expire_stale(
        self, now: datetime | None = None
    ) -> list[QueuedNotification]:
        """Expire notifications past their expiry time and prune them."""
        reference = now or dt_util.utcnow()
        expired_items: list[QueuedNotification] = []
        updated: list[QueuedNotification] = []
        changed = False
        for item in self._storage.get_queue():
            if item.status == QUEUE_STATUS_PENDING and item.expires <= reference:
                item.status = QUEUE_STATUS_EXPIRED
                expired_items.append(item)
                changed = True
                _LOGGER.debug("Expiring notification %s", item.id)
                continue
            if item.status == QUEUE_STATUS_EXPIRED:
                changed = True
                continue
            updated.append(item)
        if changed:
            self._storage.set_queue(updated)
            await self._storage.async_save()
        return expired_items

    async def mark_failed(self, notification_id: str) -> None:
        """Remove a failed notification from the queue."""
        queue = [
            item for item in self._storage.get_queue() if item.id != notification_id
        ]
        self._storage.set_queue(queue)
        await self._storage.async_save()
        _LOGGER.debug("Removed failed notification %s from queue", notification_id)
