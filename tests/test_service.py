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
    """Service queues notifications when no recipients are found."""
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
            "strategy": "everyone_home",
            "queue_if_no_candidate": True,
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
                "strategy": "everyone_home",
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
    """Send with everyone and a persons filter delivers only to that person."""
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
                "strategy": "everyone",
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
    """Send with everyone_home and a person who is away queues and stores the filter."""
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
            "strategy": "everyone_home",
            "persons": ["person.alice"],
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    pending = coordinator.queue_manager.list_pending()
    assert len(pending) == 1
    assert pending[0].payload.persons == ["person.alice"]


@pytest.mark.asyncio
async def test_service_all_unconfigured_persons_queues(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """If every requested person is unknown, the notification is queued."""
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
            "strategy": "everyone",
            "persons": ["person.carol"],
            "queue_if_no_candidate": True,
        },
        blocking=True,
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.pending_count() == 1


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


@pytest.mark.asyncio
async def test_service_rejects_template_strategy(
    hass: HomeAssistant,
    smart_notify_config_entry: MockConfigEntry,
) -> None:
    """The template strategy is no longer a valid send option."""
    with pytest.raises(vol.Invalid, match="must be one of"):
        await hass.services.async_call(
            DOMAIN,
            "send",
            {"message": "Hello", "strategy": "template"},
            blocking=True,
        )
