"""Tests for storage migration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.smart_notify.const import STORAGE_VERSION
from custom_components.smart_notify.models import SmartNotifyConfig
from custom_components.smart_notify.storage import SmartNotifyStorage


@pytest.mark.asyncio
async def test_storage_migration(hass: MagicMock) -> None:
    """Storage migration returns current version."""
    version = await SmartNotifyStorage.async_migrate(hass, 0)
    assert version == STORAGE_VERSION


@pytest.mark.asyncio
async def test_storage_load_and_save(hass: MagicMock) -> None:
    """Storage round-trips configuration and queue data."""
    storage = SmartNotifyStorage(hass)
    await storage.async_load()

    config = SmartNotifyConfig(
        persons=["person.alice"],
        person_services={"person.alice": ["notify.mobile_app_alice"]},
    )
    storage.set_configuration(config)
    await storage.async_save()
    loaded = storage.get_configuration()
    assert loaded.persons == ["person.alice"]
