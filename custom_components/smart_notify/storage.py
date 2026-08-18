"""Persistent storage for Smart Notify."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import LOGGER_NAME, STORAGE_KEY, STORAGE_VERSION
from .models import QueuedNotification

_LOGGER = logging.getLogger(LOGGER_NAME)


class SmartNotifyStorage:
    """Manage Smart Notify persistent queue data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
        )
        self._data: dict[str, Any] = {"queue": []}

    async def async_load(self) -> None:
        """Load queue data from disk."""
        stored = await self._store.async_load()
        if stored is None:
            _LOGGER.debug("No existing storage found, using defaults")
            return

        if not isinstance(stored, dict):
            _LOGGER.warning("Ignoring invalid Smart Notify storage payload")
            return

        queue_data = stored.get("queue", [])
        if not isinstance(queue_data, list):
            _LOGGER.warning("Ignoring invalid Smart Notify queue storage payload")
            return

        self._data = {"queue": queue_data}
        _LOGGER.debug(
            "Loaded storage with %d queued notifications",
            len(self._data["queue"]),
        )

    async def async_save(self) -> None:
        """Persist queue data to disk."""
        await self._store.async_save(self._data)
        _LOGGER.debug("Storage saved")

    def get_queue(self) -> list[QueuedNotification]:
        """Return queued notifications."""
        return [
            QueuedNotification.from_dict(item) for item in self._data.get("queue", [])
        ]

    def set_queue(self, queue: list[QueuedNotification]) -> None:
        """Replace queue contents."""
        self._data["queue"] = [item.to_dict() for item in queue]

    def as_dict(self) -> dict[str, Any]:
        """Return raw storage data for diagnostics."""
        return dict(self._data)
