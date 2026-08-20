"""Tests for coordinator payload builder."""

from __future__ import annotations

from datetime import timedelta

from custom_components.smart_notify.const import (
    ATTR_ACTIONS,
    ATTR_EXPIRE_AFTER,
    ATTR_LEVEL,
    ATTR_MESSAGE,
    ATTR_PERSONS,
    ATTR_STRATEGY,
    ATTR_TAG,
    ATTR_TITLE,
    ATTR_TOLERANCE,
    ATTR_URL,
)
from custom_components.smart_notify.coordinator.payload import build_payload
from custom_components.smart_notify.models import SmartNotifyConfig


def _config() -> SmartNotifyConfig:
    """Build a Smart Notify config for payload tests."""
    return SmartNotifyConfig(
        persons=["person.alice"],
        person_services={"person.alice": ["notify.mobile_app_alice"]},
        default_strategy="arrival",
        default_tolerance=250,
        default_expire_after="2h",
    )


def test_build_payload_uses_config_defaults() -> None:
    """Missing service fields fall back to integration defaults."""
    config = _config()
    payload = build_payload(config, {ATTR_MESSAGE: "Hello"})

    assert payload.message == "Hello"
    assert payload.title is None
    assert payload.strategy == "arrival"
    assert payload.tolerance == 250
    assert payload.level == "normal"
    assert payload.persons is None
    assert payload.expires - payload.created == timedelta(hours=2)
    assert payload.id


def test_build_payload_applies_service_overrides() -> None:
    """Service call fields override integration defaults."""
    config = _config()
    payload = build_payload(
        config,
        {
            ATTR_MESSAGE: "Washer done",
            ATTR_TITLE: "Laundry",
            ATTR_STRATEGY: "closest",
            ATTR_TOLERANCE: 750,
            ATTR_EXPIRE_AFTER: "30m",
            ATTR_LEVEL: "important",
            ATTR_TAG: "laundry",
            ATTR_URL: "/lovelace/laundry",
            ATTR_PERSONS: ["person.alice"],
            ATTR_ACTIONS: [{"action": "ACK", "title": "Got it"}],
        },
    )

    assert payload.title == "Laundry"
    assert payload.strategy == "closest"
    assert payload.tolerance == 750
    assert payload.level == "important"
    assert payload.tag == "laundry"
    assert payload.url == "/lovelace/laundry"
    assert payload.persons == ["person.alice"]
    assert payload.actions == [{"action": "ACK", "title": "Got it"}]
    assert payload.expires - payload.created == timedelta(minutes=30)
