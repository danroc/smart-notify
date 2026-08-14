"""Tests for storage migration."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.smart_notify.const import STORAGE_VERSION
from custom_components.smart_notify.models import NotificationPayload
from custom_components.smart_notify.queue import QueueManager
from custom_components.smart_notify.storage import SmartNotifyStorage


@pytest.mark.asyncio
async def test_storage_migration(hass: MagicMock) -> None:
    """Storage migration returns current version."""
    version = await SmartNotifyStorage.async_migrate(hass, 0)
    assert version == STORAGE_VERSION


@pytest.mark.asyncio
async def test_storage_load_and_save(hass: MagicMock) -> None:
    """Storage round-trips queue data."""
    storage = SmartNotifyStorage(hass)
    await storage.async_load()

    now = dt_util.utcnow()
    payload = NotificationPayload(
        id="queued-1",
        title="Test",
        message="Hello",
        strategy="arrival",
        tag=None,
        level="normal",
        group=None,
        image=None,
        url=None,
        created=now,
        expires=now + timedelta(hours=1),
    )
    queue = QueueManager(storage)
    await queue.enqueue(payload)
    await storage.async_save()

    reloaded = SmartNotifyStorage(hass)
    await reloaded.async_load()
    assert len(reloaded.get_queue()) == 1
    assert reloaded.get_queue()[0].id == "queued-1"


@pytest.mark.asyncio
async def test_storage_load_ignores_legacy_keys(hass: MagicMock) -> None:
    """Legacy storage keys are dropped when loading queue data."""
    storage = SmartNotifyStorage(hass)
    storage._store.async_load = AsyncMock(
        return_value={
            "configuration": {"persons": ["person.alice"]},
            "last_deliveries": [{"notification_id": "old"}],
            "errors": [{"notification_id": "old"}],
            "queue": [],
        }
    )

    await storage.async_load()

    assert storage.as_dict() == {"queue": []}
