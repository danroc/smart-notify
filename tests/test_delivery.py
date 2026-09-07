"""Tests for delivery manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import pytest

from custom_components.smart_notify.delivery import DeliveryManager
from custom_components.smart_notify.delivery.notify_data import build_notify_data
from custom_components.smart_notify.models import SmartNotifyConfig
from tests.conftest import make_delivery_payload, make_payload


@dataclass
class FakeNotifyPort:
    """In-memory notify port for testing DeliveryManager in isolation."""

    fail_targets: set[str] = field(default_factory=set)
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def send(self, target: str, data: dict[str, Any]) -> None:
        """Record the call, raising for configured failing targets."""
        if target in self.fail_targets:
            msg = f"simulated failure for {target}"
            raise ValueError(msg)
        self.calls.append((target, data))


@pytest.fixture
def notify_port() -> FakeNotifyPort:
    """Create a fake notify port."""
    return FakeNotifyPort()


@pytest.fixture
def delivery_manager(notify_port: FakeNotifyPort) -> DeliveryManager:
    """Create a delivery manager."""
    config = SmartNotifyConfig(
        persons=["person.alice"],
        person_services={"person.alice": ["notify.mobile_app_alice"]},
    )
    return DeliveryManager(notify_port, config)


def test_build_notify_data_merges_actions_tag_and_url() -> None:
    """Top-level fields land in notify data without double nesting."""
    payload = make_delivery_payload(
        actions=[{"action": "ACK", "title": "Got it"}],
        url="https://example.com",
        group="alerts",
    )
    data = build_notify_data(payload)
    assert data["message"] == "Message"
    assert data["title"] == "Title"
    assert data["data"] == {
        "url": "https://example.com",
        "clickAction": "https://example.com",
        "group": "alerts",
        "tag": "tag",
        "actions": [{"action": "ACK", "title": "Got it"}],
    }
    assert "actions" not in data


def test_build_notify_data_omits_click_action_without_url() -> None:
    """No tap target is sent when the payload has no url."""
    data = build_notify_data(make_delivery_payload(url=None))
    assert "url" not in data["data"]
    assert "clickAction" not in data["data"]


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        ("silent", {"push": {"interruption-level": "passive"}}),
        (
            "important",
            {
                "priority": "high",
                "ttl": 0,
                "push": {"interruption-level": "time-sensitive"},
            },
        ),
        (
            "critical",
            {
                "priority": "high",
                "ttl": 0,
                "push": {"interruption-level": "critical"},
            },
        ),
    ],
)
def test_build_notify_data_maps_level_to_notify_data(
    level: str, expected: dict[str, object]
) -> None:
    """Non-normal levels add the iOS push block and Android delivery fields."""
    payload = make_delivery_payload(level=level, tag=None)
    data = build_notify_data(payload)
    assert data["data"] == expected


def test_build_notify_data_does_not_share_push_dict() -> None:
    """Built payloads own their push block rather than the level constant."""
    first = build_notify_data(make_delivery_payload(level="critical", tag=None))
    first["data"]["push"]["interruption-level"] = "mutated"
    second = build_notify_data(make_delivery_payload(level="critical", tag=None))
    assert second["data"]["push"] == {"interruption-level": "critical"}


def test_build_notify_data_omits_level_fields_for_normal_level() -> None:
    """Normal level adds no push block or Android delivery fields."""
    payload = make_delivery_payload(tag="tag")
    data = build_notify_data(payload)
    assert data["data"] == {"tag": "tag"}


def test_build_notify_data_omits_data_when_empty() -> None:
    """Plain notifications do not include an empty notify data block."""
    payload = make_payload(
        "plain",
        title=None,
        message="Message",
        expires_delta=timedelta(),
    )
    data = build_notify_data(payload)
    assert data == {"message": "Message"}


def test_build_notify_data_keeps_message_key_when_empty() -> None:
    """The message key is always present, even if its value is empty."""
    payload = make_payload(
        "empty-message",
        title=None,
        message="",
        expires_delta=timedelta(),
    )
    data = build_notify_data(payload)
    assert data == {"message": ""}


@pytest.mark.asyncio
async def test_delivery_sends_to_configured_service(
    delivery_manager: DeliveryManager,
    notify_port: FakeNotifyPort,
) -> None:
    """Deliver through the notify port using the recipient's configured service."""
    record = await delivery_manager.deliver(make_delivery_payload(), ["person.alice"])

    assert record.success is True
    assert record.services == ["notify.mobile_app_alice"]
    assert len(notify_port.calls) == 1
    target, data = notify_port.calls[0]
    assert target == "notify.mobile_app_alice"
    assert data["message"] == "Message"
    assert data["data"]["tag"] == "tag"


@pytest.mark.asyncio
async def test_delivery_fails_when_target_missing(
    delivery_manager: DeliveryManager,
    notify_port: FakeNotifyPort,
) -> None:
    """Fail clearly when the notify port cannot reach the target."""
    delivery_manager._config.person_services = {
        "person.alice": ["notify.missing"],
    }
    notify_port.fail_targets = {"notify.missing"}

    record = await delivery_manager.deliver(make_delivery_payload(), ["person.alice"])

    assert record.success is False
    assert record.services == []
    assert record.error is not None
    assert "notify.missing" in record.error
    assert notify_port.calls == []


@pytest.mark.asyncio
async def test_partial_delivery_counts_as_success(
    delivery_manager: DeliveryManager,
    notify_port: FakeNotifyPort,
) -> None:
    """At least one successful notify service is enough for success."""
    delivery_manager._config.person_services = {
        "person.alice": ["notify.ok", "notify.bad"],
    }
    notify_port.fail_targets = {"notify.bad"}

    record = await delivery_manager.deliver(make_delivery_payload(), ["person.alice"])

    assert record.success is True
    assert record.services == ["notify.ok"]
    assert record.error is not None
    assert "notify.bad" in record.error
