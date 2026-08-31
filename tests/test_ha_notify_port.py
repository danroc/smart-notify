"""Tests for the Home Assistant notify port adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.smart_notify.delivery import HassNotifyPort
from custom_components.smart_notify.delivery.mobile_app import (
    resolve_legacy_mobile_app_service,
)
from custom_components.smart_notify.delivery.notify_data import build_notify_data
from tests.conftest import make_delivery_payload

LEGACY_MOBILE_APP_SERVICE = "mobile_app_daniel_iphone"


def _has_legacy_mobile_app_service(domain: str, service: str) -> bool:
    return domain == "notify" and service == LEGACY_MOBILE_APP_SERVICE


@pytest.fixture
def ha_notify_port(mock_hass: MagicMock) -> HassNotifyPort:
    """Create a notify port bound to a mocked Home Assistant."""
    return HassNotifyPort(mock_hass)


def _data(**overrides: object) -> dict[str, object]:
    return build_notify_data(make_delivery_payload(**overrides))


@pytest.mark.asyncio
async def test_send_calls_legacy_notify_service(
    mock_hass: MagicMock,
    ha_notify_port: HassNotifyPort,
) -> None:
    """Deliver through legacy notify services when registered."""
    mock_hass.services.has_service.return_value = True
    mock_hass.services.async_call = AsyncMock()

    await ha_notify_port.send("notify.mobile_app_alice", _data())

    mock_hass.services.async_call.assert_awaited_once()
    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0] == "notify"
    assert call_args.args[1] == "mobile_app_alice"


@pytest.mark.asyncio
async def test_send_legacy_notify_service_includes_actions(
    mock_hass: MagicMock,
    ha_notify_port: HassNotifyPort,
) -> None:
    """Legacy notify services receive actions in data.actions."""
    mock_hass.services.has_service.return_value = True
    mock_hass.services.async_call = AsyncMock()

    await ha_notify_port.send(
        "notify.mobile_app_alice",
        _data(actions=[{"action": "ACK", "title": "Got it"}]),
    )

    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    notify_data = call_args.args[2]["data"]
    assert notify_data["actions"] == [{"action": "ACK", "title": "Got it"}]
    assert notify_data["tag"] == "tag"


@pytest.mark.asyncio
async def test_send_calls_notify_send_message_for_entity(
    mock_hass: MagicMock,
    ha_notify_port: HassNotifyPort,
) -> None:
    """Deliver via notify.send_message when the target is a notify entity."""
    mock_hass.services.has_service.return_value = False
    mock_hass.states.get.return_value = MagicMock()
    mock_hass.services.async_call = AsyncMock()

    await ha_notify_port.send(
        "notify.daniel_iphone",
        _data(tag=None, url=None, group=None),
    )

    mock_hass.services.async_call.assert_awaited_once()
    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0] == "notify"
    assert call_args.args[1] == "send_message"
    assert call_args.args[2] == {"message": "Message", "title": "Title"}
    assert call_args.kwargs["target"] == {"entity_id": "notify.daniel_iphone"}


@pytest.mark.asyncio
async def test_send_entity_with_actions_uses_legacy_service(
    mock_hass: MagicMock,
    ha_notify_port: HassNotifyPort,
) -> None:
    """Resolve notify entities to legacy mobile_app services for rich payloads."""
    mock_hass.services.has_service.side_effect = _has_legacy_mobile_app_service
    mock_hass.states.get.return_value = MagicMock()
    mock_hass.services.async_call = AsyncMock()

    with patch(
        "custom_components.smart_notify.delivery.ha_notify_port"
        ".resolve_legacy_mobile_app_service",
        return_value=("notify", "mobile_app_daniel_iphone"),
    ):
        await ha_notify_port.send(
            "notify.daniel_iphone",
            _data(actions=[{"action": "ACK", "title": "Got it"}], url=None, group=None),
        )

    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0:2] == ("notify", LEGACY_MOBILE_APP_SERVICE)
    actions = call_args.args[2]["data"]["actions"]
    assert actions == [{"action": "ACK", "title": "Got it"}]


@pytest.mark.asyncio
async def test_send_entity_with_level_only_uses_legacy_service(
    mock_hass: MagicMock,
    ha_notify_port: HassNotifyPort,
) -> None:
    """Level alone is enough to require the legacy mobile_app notify path."""
    mock_hass.services.has_service.side_effect = _has_legacy_mobile_app_service
    mock_hass.states.get.return_value = MagicMock()
    mock_hass.services.async_call = AsyncMock()

    with patch(
        "custom_components.smart_notify.delivery.ha_notify_port"
        ".resolve_legacy_mobile_app_service",
        return_value=("notify", "mobile_app_daniel_iphone"),
    ):
        await ha_notify_port.send(
            "notify.daniel_iphone",
            _data(level="critical", tag=None, url=None, group=None),
        )

    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0:2] == ("notify", LEGACY_MOBILE_APP_SERVICE)
    assert call_args.args[2]["data"]["push"] == {"interruption-level": "critical"}
    assert call_args.args[2]["data"]["priority"] == "high"
    assert call_args.args[2]["data"]["ttl"] == 0


@pytest.mark.asyncio
async def test_send_entity_with_actions_falls_back_to_plain_send_message(
    mock_hass: MagicMock,
    ha_notify_port: HassNotifyPort,
) -> None:
    """Drop actions when a notify entity cannot resolve to a legacy service."""
    mock_hass.services.has_service.return_value = False
    mock_hass.states.get.return_value = MagicMock()
    mock_hass.services.async_call = AsyncMock()

    with patch(
        "custom_components.smart_notify.delivery.ha_notify_port"
        ".resolve_legacy_mobile_app_service",
        return_value=None,
    ):
        await ha_notify_port.send(
            "notify.daniel_iphone",
            _data(actions=[{"action": "ACK", "title": "Got it"}], url=None, group=None),
        )

    call_args = mock_hass.services.async_call.await_args
    assert call_args is not None
    assert call_args.args[0:2] == ("notify", "send_message")
    assert call_args.args[2] == {"message": "Message", "title": "Title"}


@pytest.mark.asyncio
async def test_send_raises_when_target_missing(
    mock_hass: MagicMock,
    ha_notify_port: HassNotifyPort,
) -> None:
    """Raise clearly when the target is neither a service nor a notify entity."""
    mock_hass.services.has_service.return_value = False
    mock_hass.states.get.return_value = None
    mock_hass.services.async_call = AsyncMock()

    with pytest.raises(ValueError, match=r"notify\.missing"):
        await ha_notify_port.send("notify.missing", _data())

    mock_hass.services.async_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_raises_for_malformed_target(
    mock_hass: MagicMock,
    ha_notify_port: HassNotifyPort,
) -> None:
    """Raise clearly when the target has no domain/service separator."""
    mock_hass.services.async_call = AsyncMock()

    with pytest.raises(ValueError, match="Invalid notify target: bogus"):
        await ha_notify_port.send("bogus", _data())

    mock_hass.services.async_call.assert_not_awaited()


def test_resolve_legacy_mobile_app_service(mock_hass: MagicMock) -> None:
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
            "custom_components.smart_notify.delivery.mobile_app.er.async_get",
            return_value=entity_registry,
        ),
        patch(
            "custom_components.smart_notify.delivery.mobile_app.dr.async_get",
            return_value=device_registry,
        ),
    ):
        result = resolve_legacy_mobile_app_service(
            mock_hass,
            "notify.daniel_iphone",
        )

    assert result == ("notify", "mobile_app_daniel_iphone")
    entity_registry.async_get.assert_called_once_with("notify.daniel_iphone")
    device_registry.async_get.assert_called_once_with("device-uuid")


def test_resolve_legacy_mobile_app_service_returns_none_for_other_platforms(
    mock_hass: MagicMock,
) -> None:
    """Only mobile_app notify entities can resolve to legacy services."""
    entity_entry = MagicMock()
    entity_entry.platform = "telegram"
    entity_entry.device_id = "device-uuid"

    entity_registry = MagicMock()
    entity_registry.async_get.return_value = entity_entry

    with patch(
        "custom_components.smart_notify.delivery.mobile_app.er.async_get",
        return_value=entity_registry,
    ):
        result = resolve_legacy_mobile_app_service(
            mock_hass,
            "notify.telegram_bot",
        )

    assert result is None
