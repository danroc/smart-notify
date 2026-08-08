"""Tests for person arrival queue flush."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util

from custom_components.smart_notify.const import DOMAIN
from custom_components.smart_notify.models import DeliveryRecord

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_person_arrival_flushes_queue(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Queued notifications deliver when a person arrives home."""
    hass.states.async_set(
        "person.alice",
        "not_home",
        {"latitude": 40.0, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Laundry",
            "strategy": "everyone_home",
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1

    hass.states.async_set(
        "person.alice",
        "home",
        {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
    )
    record = DeliveryRecord(
        notification_id="queued",
        recipients=["person.alice"],
        services=["notify.mobile_app_alice"],
        delivered_at=dt_util.utcnow(),
        success=True,
    )
    with patch.object(
        coordinator._delivery,
        "deliver",
        AsyncMock(return_value=record),
    ):
        await coordinator._async_on_person_arrival(
            "person.alice",
            State("person.alice", "not_home"),
            State("person.alice", "home"),
        )

    assert coordinator.pending_count() == 0
    assert coordinator.delivered_today() == 1


@pytest.mark.asyncio
async def test_restart_persistence(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Queued notifications survive coordinator reload."""
    hass.states.async_set(
        "person.alice",
        "not_home",
        {"latitude": 40.0, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {"message": "Persist me", "strategy": "everyone_home"},
        blocking=True,
    )
    storage = hass.data[DOMAIN]["storage"]
    await storage.async_save()

    new_storage = type(storage)(hass)
    await new_storage.async_load()
    assert len(new_storage.get_queue()) == 1


@pytest.mark.asyncio
async def test_zone_to_home_flushes_queue(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Arrival from a named zone flushes the queue."""
    hass.states.async_set(
        "person.alice",
        "Work",
        {"latitude": 40.0, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Laundry",
            "strategy": "everyone_home",
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1

    hass.states.async_set(
        "person.alice",
        "home",
        {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
    )
    record = DeliveryRecord(
        notification_id="queued",
        recipients=["person.alice"],
        services=["notify.mobile_app_alice"],
        delivered_at=dt_util.utcnow(),
        success=True,
    )
    with patch.object(
        coordinator._delivery,
        "deliver",
        AsyncMock(return_value=record),
    ):
        await coordinator._async_on_person_arrival(
            "person.alice",
            State("person.alice", "Work"),
            State("person.alice", "home"),
        )

    assert coordinator.pending_count() == 0
    assert coordinator.delivered_today() == 1


@pytest.mark.asyncio
async def test_failed_flush_does_not_retry(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Failed queue delivery leaves the item non-pending so it is not retried."""
    hass.states.async_set(
        "person.alice",
        "not_home",
        {"latitude": 40.0, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Laundry",
            "strategy": "everyone_home",
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1

    hass.states.async_set(
        "person.alice",
        "home",
        {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
    )
    failed = DeliveryRecord(
        notification_id="queued",
        recipients=["person.alice"],
        services=["notify.mobile_app_alice"],
        delivered_at=dt_util.utcnow(),
        success=False,
        error="boom",
    )
    deliver = AsyncMock(return_value=failed)
    with patch.object(coordinator._delivery, "deliver", deliver):
        await coordinator._async_on_person_arrival(
            "person.alice",
            State("person.alice", "not_home"),
            State("person.alice", "home"),
        )
        await coordinator._async_on_person_arrival(
            "person.alice",
            State("person.alice", "not_home"),
            State("person.alice", "home"),
        )

    assert deliver.await_count == 1
    assert coordinator.pending_count() == 0
    assert coordinator.failed_today() == 1
