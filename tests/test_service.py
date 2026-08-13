"""Tests for smart_notify.send service."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.util import dt as dt_util

from custom_components.smart_notify.const import DOMAIN
from custom_components.smart_notify.models import DeliveryRecord
from tests.conftest import make_config_entry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_service_validation_requires_message(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Service rejects calls without a message."""
    with pytest.raises(vol.Invalid, match="required key not provided"):
        await hass.services.async_call(
            DOMAIN,
            "send",
            {},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_service_send_queues_when_no_recipients(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Arrival queues by default when nobody is home."""
    hass.states.async_set(
        "person.alice",
        "not_home",
        {"latitude": 40.0, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Washing machine finished.",
            "strategy": "arrival",
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1


@pytest.mark.asyncio
async def test_service_send_delivers_to_home_recipients(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Service delivers immediately when recipients are available."""
    hass.states.async_set(
        "person.alice",
        "home",
        {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    record = DeliveryRecord(
        notification_id="test",
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
        await hass.services.async_call(
            DOMAIN,
            "send",
            {
                "message": "Hello",
                "strategy": "home",
            },
            blocking=True,
        )
    assert coordinator.delivered_today() == 1


@pytest.mark.asyncio
async def test_service_rejects_empty_persons(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """An empty persons list is invalid."""
    with pytest.raises(vol.Invalid, match="length"):
        await hass.services.async_call(
            DOMAIN,
            "send",
            {"message": "Hello", "persons": []},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_service_send_filters_persons(hass: HomeAssistant) -> None:
    """Send with direct and a persons filter delivers only to that person."""
    entry = make_config_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for entity_id in ("person.alice", "person.bob"):
        hass.states.async_set(
            entity_id,
            "home",
            {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
        )
    coordinator = hass.data[DOMAIN]["coordinator"]
    record = DeliveryRecord(
        notification_id="test",
        recipients=["person.alice"],
        services=["notify.mobile_app_alice"],
        delivered_at=dt_util.utcnow(),
        success=True,
    )
    deliver = AsyncMock(return_value=record)
    with patch.object(coordinator._delivery, "deliver", deliver):
        await hass.services.async_call(
            DOMAIN,
            "send",
            {
                "message": "Hello",
                "strategy": "direct",
                "persons": ["person.alice"],
            },
            blocking=True,
        )
    deliver.assert_awaited_once()
    assert deliver.await_args is not None
    assert deliver.await_args.args[1] == ["person.alice"]


@pytest.mark.asyncio
async def test_service_queues_when_filtered_person_is_away(
    hass: HomeAssistant,
) -> None:
    """Arrival with a person who is away queues and stores the filter."""
    entry = make_config_entry()
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
        "home",
        {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Hello",
            "strategy": "arrival",
            "persons": ["person.alice"],
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    pending = coordinator.queue_manager.list_pending()
    assert len(pending) == 1
    assert pending[0].payload.persons == ["person.alice"]


@pytest.mark.asyncio
async def test_service_all_unconfigured_persons_queues_when_flag_set(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Unknown persons queue only when queue_if_no_candidate is true."""
    hass.states.async_set(
        "person.alice",
        "home",
        {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Hello",
            "strategy": "direct",
            "persons": ["person.carol"],
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1


@pytest.mark.asyncio
async def test_home_does_not_queue_by_default(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Home is a snapshot: nobody home means drop, not wait."""
    hass.states.async_set(
        "person.alice",
        "not_home",
        {"latitude": 40.0, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {"message": "Hello", "strategy": "home"},
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 0


@pytest.mark.asyncio
async def test_away_does_not_queue_by_default(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Away is a snapshot: nobody away means drop, not wait for departure."""
    hass.states.async_set(
        "person.alice",
        "home",
        {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {"message": "Hello", "strategy": "away"},
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 0


@pytest.mark.asyncio
async def test_home_queues_when_flag_true(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Explicit queue_if_no_candidate still queues a home snapshot."""
    hass.states.async_set(
        "person.alice",
        "not_home",
        {"latitude": 40.0, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Hello",
            "strategy": "home",
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1


@pytest.mark.asyncio
async def test_arrival_does_not_queue_when_flag_false(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Explicit false disables arrival queueing."""
    hass.states.async_set(
        "person.alice",
        "not_home",
        {"latitude": 40.0, "longitude": -74.0},
    )
    await hass.services.async_call(
        DOMAIN,
        "send",
        {
            "message": "Hello",
            "strategy": "arrival",
            "queue_if_no_candidate": False,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 0


@pytest.mark.asyncio
async def test_closest_queues_by_default_without_coordinates(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Closest with no usable GPS queues until someone can be located."""
    hass.states.async_set("person.alice", "not_home", {})
    await hass.services.async_call(
        DOMAIN,
        "send",
        {"message": "Hello", "strategy": "closest"},
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1


@pytest.mark.asyncio
async def test_legacy_default_strategy_sends_without_strategy_field(
    hass: HomeAssistant,
) -> None:
    """A config entry still storing everyone treats omitted strategy as direct."""
    entry = make_config_entry(default_strategy="everyone")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for entity_id in ("person.alice", "person.bob"):
        hass.states.async_set(
            entity_id,
            "home",
            {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
        )
    coordinator = hass.data[DOMAIN]["coordinator"]
    record = DeliveryRecord(
        notification_id="test",
        recipients=["person.alice", "person.bob"],
        services=["notify.mobile_app_alice"],
        delivered_at=dt_util.utcnow(),
        success=True,
    )
    deliver = AsyncMock(return_value=record)
    with patch.object(coordinator._delivery, "deliver", deliver):
        await hass.services.async_call(
            DOMAIN,
            "send",
            {"message": "Hello"},
            blocking=True,
        )
    deliver.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_rejects_non_person_entities(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """Persons must be person domain entity IDs."""
    with pytest.raises(vol.Invalid, match="person"):
        await hass.services.async_call(
            DOMAIN,
            "send",
            {"message": "Hello", "persons": ["light.kitchen"]},
            blocking=True,
        )


@pytest.mark.parametrize(
    "strategy",
    ["template", "everyone", "everyone_home", "everyone_away", "first_home"],
)
@pytest.mark.asyncio
async def test_service_rejects_removed_strategies(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
    strategy: str,
) -> None:
    """Removed strategy names are rejected by the send schema."""
    with pytest.raises(vol.Invalid, match="must be one of"):
        await hass.services.async_call(
            DOMAIN,
            "send",
            {"message": "Hello", "strategy": strategy},
            blocking=True,
        )
