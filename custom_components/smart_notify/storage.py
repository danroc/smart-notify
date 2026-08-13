"""Persistent storage for Smart Notify."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import LOGGER_NAME, STORAGE_KEY, STORAGE_VERSION
from .models import QueuedNotification, SmartNotifyConfig

_LOGGER = logging.getLogger(LOGGER_NAME)


class SmartNotifyStorage:
    """Manage Smart Notify persistent data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
        )
        self._data: dict[str, Any] = {
            "configuration": {},
            "queue": [],
            "last_deliveries": [],
            "errors": [],
        }

    async def async_load(self) -> None:
        """Load data from disk."""
        stored = await self._store.async_load()
        if stored is None:
            _LOGGER.debug("No existing storage found, using defaults")
            return
        self._data.update(stored)
        _LOGGER.debug(
            "Loaded storage with %d queued notifications",
            len(self._data.get("queue", [])),
        )

    async def async_save(self) -> None:
        """Persist data to disk."""
        await self._store.async_save(self._data)
        _LOGGER.debug("Storage saved")

    def set_configuration(self, config: SmartNotifyConfig) -> None:
        """Store integration configuration."""
        self._data["configuration"] = config.to_dict()

    def get_configuration(self) -> SmartNotifyConfig:
        """Return stored configuration."""
        return SmartNotifyConfig.from_entry_data(self._data.get("configuration", {}))

    def get_queue(self) -> list[QueuedNotification]:
        """Return queued notifications."""
        return [
            QueuedNotification.from_dict(item) for item in self._data.get("queue", [])
        ]

    def set_queue(self, queue: list[QueuedNotification]) -> None:
        """Replace queue contents."""
        self._data["queue"] = [item.to_dict() for item in queue]

    def add_delivery(self, record: dict[str, Any]) -> None:
        """Append a delivery record."""
        deliveries = self._data.setdefault("last_deliveries", [])
        deliveries.append(record)
        self._data["last_deliveries"] = deliveries[-50:]

    def add_error(self, error: dict[str, Any]) -> None:
        """Append an error record."""
        errors = self._data.setdefault("errors", [])
        errors.append(error)
        self._data["errors"] = errors[-50:]

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
