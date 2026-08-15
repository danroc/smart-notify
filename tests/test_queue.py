"""Tests for queue persistence and expiration."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.smart_notify.queue import QueueManager
from custom_components.smart_notify.storage import SmartNotifyStorage
from tests.conftest import make_payload


@pytest.fixture
def storage(mock_hass: MagicMock) -> SmartNotifyStorage:
    """Create storage with mocked persistence."""
    store = SmartNotifyStorage(mock_hass)
    store._store.async_save = AsyncMock()
    return store


@pytest.fixture
def queue_manager(storage: SmartNotifyStorage) -> QueueManager:
    """Create a queue manager."""
    return QueueManager(storage)


@pytest.mark.asyncio
async def test_queue_persistence(queue_manager: QueueManager) -> None:
    """Queue items remain available after enqueue."""
    payload = make_payload("abc123", expires_delta=timedelta(hours=1))
    queued = await queue_manager.enqueue(payload)
    assert queued.id == "abc123"
    assert queue_manager.count_pending() == 1


@pytest.mark.asyncio
async def test_queue_remove(queue_manager: QueueManager) -> None:
    """Queued items can be removed."""
    payload = make_payload("remove-me", expires_delta=timedelta(hours=1))
    await queue_manager.enqueue(payload)
    await queue_manager.remove("remove-me")
    assert queue_manager.count_pending() == 0


@pytest.mark.asyncio
async def test_queue_expiration(queue_manager: QueueManager) -> None:
    """Expired notifications are removed from storage."""
    payload = make_payload("expired", expires_delta=timedelta(hours=-1))
    await queue_manager.enqueue(payload)
    expired = await queue_manager.expire_stale()
    assert len(expired) == 1
    assert expired[0].id == "expired"
    assert queue_manager.count_pending() == 0
    assert queue_manager._storage.get_queue() == []
