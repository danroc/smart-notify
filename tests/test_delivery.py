"""Tests for delivery manager."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.smart_notify.delivery import DeliveryManager
from custom_components.smart_notify.models import NotificationPayload, SmartNotifyConfig
from tests.conftest import make_payload

LEGACY_MOBILE_APP_SERVICE = "mobile_app_daniel_iphone"


def _has_legacy_mobile_app_service(domain: str, service: str) -> bool:
    return domain == "notify" and service == LEGACY_MOBILE_APP_SERVICE


@pytest.fixture
def delivery_manager(mock_hass: MagicMock) -> DeliveryManager:
    """Create a delivery manager."""
    config = SmartNotifyConfig(
        persons=["person.alice"],
        person_services={"person.alice": ["notify.mobile_app_alice"]},
    )
    return DeliveryManager(mock_hass, config)


def _payload(**overrides: object) -> NotificationPayload:
    """Build a delivery test payload."""
    defaults: dict[str, object] = {
        "title": "Title",
        "message": "Message",
        "tag": "tag",
    }
    defaults.update(overrides)
    return make_payload("delivery-test", **defaults)


def test_build_notify_data_merges_actions_tag_and_url() -> None:
    """Top-level fields land in notify data without double nesting."""
    payload = _payload(
        actions=[{"action": "ACK", "title": "Got it"}],
        url="https://example.com",
        group="alerts",
    )
    data = DeliveryManager._build_notify_data(payload)
    assert data["message"] == "Message"
    assert data["title"] == "Title"
    assert data["data"] == {
        "url": "https://example.com",
        "group": "alerts",
        "tag": "tag",
        "actions": [{"action": "ACK", "title": "Got it"}],
    }
    assert "actions" not in data


@pytest.mark.parametrize(
    ("level", "interruption"),
    [
        ("silent", "passive"),
        ("critical", "critical"),
    ],
)
def test_build_notify_data_maps_level_to_push(level: str, interruption: str) -> None:
    """Non-normal levels set the companion interruption level."""
    payload = _payload(level=level, tag=None)
    data = DeliveryManager._build_notify_data(payload)
    assert data["data"]["push"] == {"interruption-level": interruption}


def test_build_notify_data_omits_push_for_normal_level() -> None:
    """Normal level does not add a push block."""
    payload = _payload(tag="tag")
    data = DeliveryManager._build_notify_data(payload)
    assert "push" not in data["data"]


def test_build_notify_data_omits_data_when_empty() -> None:
    """Plain notifications do not include an empty notify data block."""
    payload = make_payload(
        "plain",
        title=None,
        message="Message",
        expires_delta=timedelta(),
    )
    data = DeliveryManager._build_notify_data(payload)
    assert data == {"message": "Message"}


@pytest.mark.asyncio
async def test_delivery_legacy_includes_actions(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Legacy notify services receive actions in data.actions."""
    mock_hass.services.has_service.return_value = True
    mock_hass.services.async_call = AsyncMock()
    await delivery_manager.deliver(
        _payload(actions=[{"action": "ACK", "title": "Got it"}]),
        ["person.alice"],
    )
    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    notify_data = call_args.args[2]["data"]
    assert notify_data["actions"] == [{"action": "ACK", "title": "Got it"}]
    assert notify_data["tag"] == "tag"


@pytest.mark.asyncio
async def test_delivery_calls_legacy_notify_service(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Deliver through legacy notify services when registered."""
    mock_hass.services.has_service.return_value = True
    mock_hass.services.async_call = AsyncMock()
    record = await delivery_manager.deliver(_payload(), ["person.alice"])
    assert record.success is True
    mock_hass.services.async_call.assert_awaited_once()
    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0] == "notify"
    assert call_args.args[1] == "mobile_app_alice"


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
    record = await delivery_manager.deliver(
        _payload(tag=None, url=None, group=None),
        ["person.alice"],
    )

    assert record.success is True
    mock_hass.services.async_call.assert_awaited_once()
    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0] == "notify"
    assert call_args.args[1] == "send_message"
    assert call_args.args[2] == {"message": "Message", "title": "Title"}
    assert call_args.kwargs["target"] == {"entity_id": "notify.daniel_iphone"}


def test_resolve_legacy_mobile_app_service(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Map a mobile_app notify entity to its legacy notify service name."""
    entity_entry = MagicMock()
    entity_entry.platform = "mobile_app"
    entity_entry.device_id = "device-uuid"

    device = MagicMock()
    device.name = "Daniel iPhone"

    entity_registry = MagicMock()
    entity_registry.async_get.return_value = entity_entry

    device_registry = MagicMock()
    device_registry.async_get.return_value = device

    mock_hass.services.has_service.side_effect = _has_legacy_mobile_app_service

    with (
        patch(
            "custom_components.smart_notify.delivery.er.async_get",
            return_value=entity_registry,
        ),
        patch(
            "custom_components.smart_notify.delivery.dr.async_get",
            return_value=device_registry,
        ),
    ):
        result = delivery_manager._resolve_legacy_mobile_app_service(
            "notify.daniel_iphone"
        )

    assert result == ("notify", "mobile_app_daniel_iphone")
    entity_registry.async_get.assert_called_once_with("notify.daniel_iphone")
    device_registry.async_get.assert_called_once_with("device-uuid")


def test_resolve_legacy_mobile_app_service_returns_none_for_other_platforms(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Only mobile_app notify entities can resolve to legacy services."""
    entity_entry = MagicMock()
    entity_entry.platform = "telegram"
    entity_entry.device_id = "device-uuid"

    entity_registry = MagicMock()
    entity_registry.async_get.return_value = entity_entry

    with patch(
        "custom_components.smart_notify.delivery.er.async_get",
        return_value=entity_registry,
    ):
        result = delivery_manager._resolve_legacy_mobile_app_service(
            "notify.telegram_bot"
        )

    assert result is None


@pytest.mark.asyncio
async def test_delivery_entity_with_actions_uses_legacy_service(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Resolve notify entities to legacy mobile_app services for rich payloads."""
    delivery_manager._config.person_services = {
        "person.alice": ["notify.daniel_iphone"],
    }
    mock_hass.services.has_service.side_effect = _has_legacy_mobile_app_service
    mock_hass.states.get.return_value = MagicMock()
    mock_hass.services.async_call = AsyncMock()
    with patch.object(
        delivery_manager,
        "_resolve_legacy_mobile_app_service",
        return_value=("notify", "mobile_app_daniel_iphone"),
    ):
        await delivery_manager.deliver(
            _payload(
                actions=[{"action": "ACK", "title": "Got it"}],
                url=None,
                group=None,
            ),
            ["person.alice"],
        )

    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0:2] == ("notify", LEGACY_MOBILE_APP_SERVICE)
    actions = call_args.args[2]["data"]["actions"]
    assert actions == [{"action": "ACK", "title": "Got it"}]


@pytest.mark.asyncio
async def test_delivery_entity_with_level_only_uses_legacy_service(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Level alone is enough to require the legacy mobile_app notify path."""
    delivery_manager._config.person_services = {
        "person.alice": ["notify.daniel_iphone"],
    }
    mock_hass.services.has_service.side_effect = _has_legacy_mobile_app_service
    mock_hass.states.get.return_value = MagicMock()
    mock_hass.services.async_call = AsyncMock()
    with patch.object(
        delivery_manager,
        "_resolve_legacy_mobile_app_service",
        return_value=("notify", "mobile_app_daniel_iphone"),
    ):
        await delivery_manager.deliver(
            _payload(level="critical", tag=None, url=None, group=None),
            ["person.alice"],
        )

    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0:2] == ("notify", LEGACY_MOBILE_APP_SERVICE)
    assert call_args.args[2]["data"]["push"] == {"interruption-level": "critical"}


@pytest.mark.asyncio
async def test_delivery_entity_with_actions_falls_back_to_plain_send_message(
    mock_hass: MagicMock,
    delivery_manager: DeliveryManager,
) -> None:
    """Drop actions when a notify entity cannot resolve to a legacy service."""
    delivery_manager._config.person_services = {
        "person.alice": ["notify.daniel_iphone"],
    }
    mock_hass.services.has_service.return_value = False
    mock_hass.states.get.return_value = MagicMock()
    mock_hass.services.async_call = AsyncMock()
    with patch.object(
        delivery_manager,
        "_resolve_legacy_mobile_app_service",
        return_value=None,
    ):
        await delivery_manager.deliver(
            _payload(
                actions=[{"action": "ACK", "title": "Got it"}],
                url=None,
                group=None,
            ),
            ["person.alice"],
        )

    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0:2] == ("notify", "send_message")
    assert call_args.args[2] == {"message": "Message", "title": "Title"}


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
