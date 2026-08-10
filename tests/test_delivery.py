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
async def test_delivery_calls_legacy_notify_service(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Deliver through legacy notify services when registered."""
    mock_hass.services.has_service.return_value = True
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
async def test_delivery_calls_notify_send_message_for_entity(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Deliver via notify.send_message when the target is a notify entity."""
    delivery_manager._config.person_services = {
        "person.alice": ["notify.daniel_iphone"],
    }
    mock_hass.services.has_service.return_value = False
    mock_hass.states.get.return_value = MagicMock()
    mock_hass.services.async_call = AsyncMock()
    delivery_manager._storage.async_save = AsyncMock()

    record = await delivery_manager.deliver(_payload(), ["person.alice"])

    assert record.success is True
    mock_hass.services.async_call.assert_awaited_once()
    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0] == "notify"
    assert call_args.args[1] == "send_message"
    assert call_args.args[2] == {"message": "Message", "title": "Title"}
    assert call_args.kwargs["target"] == {"entity_id": "notify.daniel_iphone"}


@pytest.mark.asyncio
async def test_delivery_fails_when_target_missing(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Fail clearly when the target is neither a service nor a notify entity."""
    delivery_manager._config.person_services = {
        "person.alice": ["notify.missing"],
    }
    mock_hass.services.has_service.return_value = False
    mock_hass.states.get.return_value = None
    mock_hass.services.async_call = AsyncMock()
    delivery_manager._storage.async_save = AsyncMock()

    record = await delivery_manager.deliver(_payload(), ["person.alice"])

    assert record.success is False
    assert record.services == []
    assert record.error is not None
    assert "notify.missing" in record.error
    mock_hass.services.async_call.assert_not_awaited()


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
    mock_hass.services.has_service.return_value = True

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
