"""Tests for delivery manager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.smart_notify.delivery import DeliveryManager
from custom_components.smart_notify.models import NotificationPayload, SmartNotifyConfig
from custom_components.smart_notify.storage import SmartNotifyStorage


@pytest.fixture
def delivery_manager(mock_hass: MagicMock) -> DeliveryManager:
    """Create a delivery manager."""
    config = SmartNotifyConfig(
        persons=["person.alice"],
        person_services={"person.alice": ["notify.mobile_app_alice"]},
    )
    storage = SmartNotifyStorage(mock_hass)
    return DeliveryManager(mock_hass, config, storage)


def _payload() -> NotificationPayload:
    now = dt_util.utcnow()
    return NotificationPayload(
        id="delivery-test",
        title="Title",
        message="Message",
        strategy="everyone",
        priority="normal",
        tag="tag",
        payload={"foo": "bar"},
        created=now,
        expires=now,
        metadata={},
    )


@pytest.mark.asyncio
async def test_delivery_calls_notify_service(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Deliver through configured notify services."""
    mock_hass.services.async_call = AsyncMock()
    delivery_manager._storage.async_save = AsyncMock()
    record = await delivery_manager.deliver(_payload(), ["person.alice"])
    assert record.success is True
    mock_hass.services.async_call.assert_awaited_once()
    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0] == "notify"
    assert call_args.args[1] == "mobile_app_alice"
    assert delivery_manager._storage._data["last_deliveries"]
    delivery_manager._storage.async_save.assert_awaited()


@pytest.mark.asyncio
async def test_partial_delivery_counts_as_success(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """At least one successful notify service is enough for success."""
    delivery_manager._config.person_services = {
        "person.alice": ["notify.ok", "notify.bad"],
    }
    delivery_manager._storage.async_save = AsyncMock()

    async def _call(
        domain: str,
        service: str,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        if service == "bad":
            msg = "fail"
            raise RuntimeError(msg)

    mock_hass.services.async_call = AsyncMock(side_effect=_call)
    record = await delivery_manager.deliver(_payload(), ["person.alice"])
    assert record.success is True
    assert record.services == ["notify.ok"]
    assert record.error is not None
