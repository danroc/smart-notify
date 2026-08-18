"""Tests for storage persistence."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

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
