"""Tests for person arrival queue flush."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.smart_notify.const import (
    DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
    DOMAIN,
)
from custom_components.smart_notify.models import DeliveryRecord, NotificationPayload
from tests.conftest import make_config_entry

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory


async def _advance_arrival_debounce(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    seconds: int = DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
) -> None:
    """Advance time past the arrival debounce window."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_person_arrival_flushes_queue_after_debounce(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Queued notifications deliver after the arrival debounce window."""
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
        assert coordinator.pending_count() == 1
        await _advance_arrival_debounce(hass, freezer)

    assert coordinator.pending_count() == 0
    assert coordinator.delivered_today() == 1


@pytest.mark.asyncio
async def test_arrival_debounce_waits_for_second_person(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Debounced flush includes people who arrive during the wait window."""
    entry = make_config_entry(
        default_strategy="first_home",
        arrival_debounce_seconds=30,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.states.async_set(
        "person.alice",
        "not_home",
        {"latitude": 40.0, "longitude": -74.0},
    )
    hass.states.async_set(
        "person.bob",
        "not_home",
        {"latitude": 40.1, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Laundry",
            "strategy": "first_home",
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1

    delivered: list[list[str]] = []

    async def _capture(
        payload: NotificationPayload, recipients: list[str]
    ) -> DeliveryRecord:
        delivered.append(list(recipients))
        return DeliveryRecord(
            notification_id=payload.id,
            recipients=recipients,
            services=["notify.mobile_app_alice"],
            delivered_at=dt_util.utcnow(),
            success=True,
        )

    deliver = AsyncMock(side_effect=_capture)
    with patch.object(coordinator._delivery, "deliver", deliver):
        hass.states.async_set(
            "person.alice",
            "home",
            {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
        )
        await coordinator._async_on_person_arrival(
            "person.alice",
            State("person.alice", "not_home"),
            State("person.alice", "home"),
        )
        assert coordinator.pending_count() == 1

        freezer.tick(timedelta(seconds=10))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert coordinator.pending_count() == 1

        hass.states.async_set(
            "person.bob",
            "home",
            {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
        )
        await coordinator._async_on_person_arrival(
            "person.bob",
            State("person.bob", "not_home"),
            State("person.bob", "home"),
        )
        await _advance_arrival_debounce(hass, freezer, seconds=30)

    assert coordinator.pending_count() == 0
    assert len(delivered) == 1
    assert set(delivered[0]) == {"person.alice", "person.bob"}


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
    freezer: FrozenDateTimeFactory,
) -> None:
    """Arrival from a named zone flushes the queue after debounce."""
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
        await _advance_arrival_debounce(hass, freezer)

    assert coordinator.pending_count() == 0
    assert coordinator.delivered_today() == 1


@pytest.mark.asyncio
async def test_failed_flush_does_not_retry(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
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
        await _advance_arrival_debounce(hass, freezer)

    assert deliver.await_count == 1
    assert coordinator.pending_count() == 0
    assert coordinator.failed_today() == 1


@pytest.mark.asyncio
async def test_queued_persons_filter_survives_flush(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A queued send for one person still targets only that person after arrival."""
    entry = make_config_entry(
        default_strategy="everyone_home",
        arrival_debounce_seconds=30,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    for entity_id, lon in (("person.alice", -74.0), ("person.bob", -74.1)):
        hass.states.async_set(
            entity_id,
            "not_home",
            {"latitude": 40.0, "longitude": lon},
        )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Laundry",
            "strategy": "everyone_home",
            "persons": ["person.alice"],
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1

    delivered: list[list[str]] = []

    async def _capture(
        payload: NotificationPayload, recipients: list[str]
    ) -> DeliveryRecord:
        delivered.append(list(recipients))
        return DeliveryRecord(
            notification_id=payload.id,
            recipients=recipients,
            services=["notify.mobile_app_alice"],
            delivered_at=dt_util.utcnow(),
            success=True,
        )

    deliver = AsyncMock(side_effect=_capture)
    with patch.object(coordinator._delivery, "deliver", deliver):
        for entity_id in ("person.alice", "person.bob"):
            hass.states.async_set(
                entity_id,
                "home",
                {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
            )
        await coordinator._async_on_person_arrival(
            "person.alice",
            State("person.alice", "not_home"),
            State("person.alice", "home"),
        )
        await _advance_arrival_debounce(hass, freezer)

    assert coordinator.pending_count() == 0
    assert delivered == [["person.alice"]]


@pytest.mark.asyncio
async def test_flush_unknown_strategy_marks_failed(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Queued items with a removed strategy are marked failed on flush."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    now = dt_util.utcnow()
    payload = NotificationPayload(
        id="old-template",
        title=None,
        message="Hello",
        strategy="template",
        priority="normal",
        tag=None,
        payload={},
        created=now,
        expires=now + timedelta(hours=4),
        metadata={},
    )
    await coordinator.queue_manager.enqueue(payload)
    assert coordinator.pending_count() == 1
    await coordinator._async_flush_queue()
    assert coordinator.pending_count() == 0
    assert coordinator.failed_today() == 1
