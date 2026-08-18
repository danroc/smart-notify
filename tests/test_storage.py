"""Tests for storage persistence."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.smart_notify.const import QUEUE_SCHEMA_VERSION
from custom_components.smart_notify.queue import QueueManager
from custom_components.smart_notify.storage import SmartNotifyStorage
from tests.conftest import make_payload


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
    assert reloaded.as_dict()["schema_version"] == QUEUE_SCHEMA_VERSION


@pytest.mark.asyncio
async def test_storage_save_includes_schema_version(hass: MagicMock) -> None:
    """Saved storage always includes the current queue schema version."""
    storage = SmartNotifyStorage(hass)
    await storage.async_save()

    assert storage.as_dict() == {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "queue": [],
    }


@pytest.mark.asyncio
async def test_storage_load_rejects_unversioned_data(hass: MagicMock) -> None:
    """Storage without a schema version starts from defaults."""
    storage = SmartNotifyStorage(hass)
    storage._store.async_load = AsyncMock(return_value={"queue": []})

    await storage.async_load()

    assert storage.as_dict() == {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "queue": [],
    }


@pytest.mark.asyncio
async def test_storage_load_rejects_unsupported_schema_version(
    hass: MagicMock,
) -> None:
    """Unsupported schema versions are ignored."""
    storage = SmartNotifyStorage(hass)
    storage._store.async_load = AsyncMock(
        return_value={
            "schema_version": QUEUE_SCHEMA_VERSION + 1,
            "queue": [{"id": "old", "status": "pending", "payload": {}}],
        }
    )

    await storage.async_load()

    assert storage.as_dict() == {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "queue": [],
    }


@pytest.mark.asyncio
async def test_storage_load_rejects_invalid_queue_with_valid_schema(
    hass: MagicMock,
) -> None:
    """Invalid queue payloads are ignored even when schema_version matches."""
    storage = SmartNotifyStorage(hass)
    storage._store.async_load = AsyncMock(
        return_value={
            "schema_version": QUEUE_SCHEMA_VERSION,
            "queue": "not-a-list",
        }
    )

    await storage.async_load()

    assert storage.as_dict() == {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "queue": [],
    }
