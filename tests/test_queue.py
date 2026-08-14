"""Tests for queue persistence and expiration."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.smart_notify.models import NotificationPayload
from custom_components.smart_notify.queue import QueueManager
from custom_components.smart_notify.storage import SmartNotifyStorage


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


def _payload(notification_id: str, expires: timedelta) -> NotificationPayload:
    now = dt_util.utcnow()
    return NotificationPayload(
        id=notification_id,
        title="Test",
        message="Hello",
        strategy="closest",
        tag=None,
        payload={},
        created=now,
        expires=now + expires,
    )


@pytest.mark.asyncio
async def test_queue_persistence(queue_manager: QueueManager) -> None:
    """Queue items remain available after enqueue."""
    payload = _payload("abc123", timedelta(hours=1))
    queued = await queue_manager.enqueue(payload)
    assert queued.id == "abc123"
    assert queue_manager.count_pending() == 1


@pytest.mark.asyncio
async def test_queue_remove(queue_manager: QueueManager) -> None:
    """Queued items can be removed."""
    payload = _payload("remove-me", timedelta(hours=1))
    await queue_manager.enqueue(payload)
    await queue_manager.remove("remove-me")
    assert queue_manager.count_pending() == 0


@pytest.mark.asyncio
async def test_queue_expiration(queue_manager: QueueManager) -> None:
    """Expired notifications are removed from storage."""
    payload = _payload("expired", timedelta(hours=-1))
    await queue_manager.enqueue(payload)
    expired = await queue_manager.expire_stale()
    assert len(expired) == 1
    assert expired[0].id == "expired"
    assert queue_manager.count_pending() == 0
    assert queue_manager._storage.get_queue() == []
