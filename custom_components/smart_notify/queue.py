"""Persistent notification queue management."""

from __future__ import annotations

import logging
from dataclasses import replace

from homeassistant.util import dt as dt_util

from .const import LOGGER_NAME, QUEUE_STATUS_EXPIRED, QUEUE_STATUS_PENDING
from .models import NotificationPayload, QueuedNotification
from .storage import SmartNotifyStorage
from .util import generate_id

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
        payload = replace(payload, id=payload.id or generate_id())
        queued = QueuedNotification(id=payload.id, payload=payload)

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

    async def expire_stale(self) -> list[QueuedNotification]:
        """Expire notifications past their expiry time and prune them."""
        reference = dt_util.utcnow()
        queue = self._storage.get_queue()
        expired: list[QueuedNotification] = []
        kept: list[QueuedNotification] = []

        for item in queue:
            if item.status == QUEUE_STATUS_PENDING and item.expires <= reference:
                item.status = QUEUE_STATUS_EXPIRED
                expired.append(item)
                _LOGGER.debug("Expiring notification %s", item.id)
            elif item.status != QUEUE_STATUS_EXPIRED:
                kept.append(item)

        if len(kept) != len(queue):
            self._storage.set_queue(kept)
            await self._storage.async_save()

        return expired
