"""Persistent storage for Smart Notify."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import LOGGER_NAME, STORAGE_KEY, STORAGE_VERSION
from .models import QueuedNotification

_LOGGER = logging.getLogger(LOGGER_NAME)

_LEGACY_STORAGE_KEYS = frozenset({"configuration", "last_deliveries", "errors"})


def _normalize_storage_data(stored: object) -> dict[str, Any]:
    """Return queue-only storage data."""
    if not isinstance(stored, dict):
        return {"queue": []}
    queue = stored.get("queue", [])
    if not isinstance(queue, list):
        queue = []
    return {"queue": queue}


class _SmartNotifyStore(Store[dict[str, Any]]):
    """Store with migration to queue-only persistence."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Drop legacy mirrored config and delivery history keys."""
        del old_minor_version
        if old_major_version < STORAGE_VERSION:
            return _normalize_storage_data(old_data)
        return old_data


class SmartNotifyStorage:
    """Manage Smart Notify persistent queue data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self._store = _SmartNotifyStore(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
        )
        self._data: dict[str, Any] = {
            "queue": [],
        }

    async def async_load(self) -> None:
        """Load queue data from disk."""
        stored = await self._store.async_load()
        if stored is None:
            _LOGGER.debug("No existing storage found, using defaults")
            return

        normalized = _normalize_storage_data(stored)
        self._data = normalized
        _LOGGER.debug(
            "Loaded storage with %d queued notifications",
            len(self._data["queue"]),
        )

        if isinstance(stored, dict) and _LEGACY_STORAGE_KEYS.intersection(stored):
            _LOGGER.info("Pruning legacy Smart Notify storage keys")
            await self.async_save()

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

    @staticmethod
    async def async_migrate(hass: HomeAssistant, version: int) -> int:
        """Migrate storage if needed."""
        del hass
        if version < STORAGE_VERSION:
            _LOGGER.info(
                "Migrating Smart Notify storage to version %s", STORAGE_VERSION
            )
        return STORAGE_VERSION
