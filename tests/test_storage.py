"""Tests for storage migration."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.smart_notify.queue import QueueManager
from custom_components.smart_notify.storage import SmartNotifyStorage
from tests.conftest import make_payload


@pytest.mark.asyncio
async def test_store_migrates_from_version_1(hass: MagicMock) -> None:
    """Store migration drops legacy keys when upgrading from v1."""
    store = SmartNotifyStorage(hass)._store
    migrated = await store._async_migrate_func(
        1,
        1,
        {
            "configuration": {"persons": ["person.alice"]},
            "queue": [],
        },
    )
    assert migrated == {"queue": []}


@pytest.mark.asyncio
async def test_storage_load_and_save(hass: MagicMock) -> None:
    """Storage round-trips queue data."""
    storage = SmartNotifyStorage(hass)
    await storage.async_load()

    payload = make_payload(
        "queued-1",
        strategy="arrival",
        title="Test",
        message="Hello",
        expires_delta=timedelta(hours=1),
    )
    queue = QueueManager(storage)
    await queue.enqueue(payload)
    await storage.async_save()

    reloaded = SmartNotifyStorage(hass)
    await reloaded.async_load()
    assert len(reloaded.get_queue()) == 1
    assert reloaded.get_queue()[0].id == "queued-1"


@pytest.mark.asyncio
async def test_storage_load_prunes_legacy_keys(hass: MagicMock) -> None:
    """Legacy storage keys are dropped and rewritten on load."""
    storage = SmartNotifyStorage(hass)
    storage._store.async_load = AsyncMock(
        return_value={
            "configuration": {"persons": ["person.alice"]},
            "last_deliveries": [{"notification_id": "old"}],
            "errors": [{"notification_id": "old"}],
            "queue": [],
        }
    )
    storage._store.async_save = AsyncMock()

    await storage.async_load()

    assert storage.as_dict() == {"queue": []}
    storage._store.async_save.assert_awaited_once_with({"queue": []})
