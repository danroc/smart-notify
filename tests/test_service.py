"""Tests for smart_notify.send service."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.util import dt as dt_util

from custom_components.smart_notify.const import DOMAIN
from custom_components.smart_notify.models import DeliveryRecord

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
