"""Tests for notification payload serialization."""

from __future__ import annotations

from custom_components.smart_notify.models import (
    NotificationPayload,
    QueuedNotification,
)
from tests.conftest import make_payload


def test_payload_roundtrip_preserves_level_and_url() -> None:
    """Queued payloads keep flat mobile fields across serialize/deserialize."""
    restored = NotificationPayload.from_dict(
        make_payload().to_dict() | {"level": "critical", "url": "https://example.com"}
    )
    assert restored.level == "critical"
    assert restored.url == "https://example.com"


def test_payload_from_dict_preserves_important_level() -> None:
    """Important level is stored and restored."""
    restored = NotificationPayload.from_dict(
        make_payload().to_dict() | {"level": "important"}
    )
    assert restored.level == "important"


def test_payload_from_dict_rejects_invalid_level() -> None:
    """Unknown stored levels fall back to normal."""
    restored = NotificationPayload.from_dict(
        make_payload().to_dict() | {"level": "bogus"}
    )
    assert restored.level == "normal"


def test_payload_from_dict_migrates_legacy_payload_dict() -> None:
    """Queued items with the old payload bag keep known mobile fields."""
    data = make_payload().to_dict()
    data.pop("url", None)
    data.pop("group", None)
    data["payload"] = {
        "url": "https://example.com",
        "group": "alerts",
        "tag": "legacy-tag",
    }
    restored = NotificationPayload.from_dict(data)
    assert restored.url == "https://example.com"
    assert restored.group == "alerts"
    assert restored.tag == "legacy-tag"


def test_payload_roundtrip_preserves_actions() -> None:
    """Queued payloads keep actions across serialize/deserialize."""
    actions = [{"action": "ACK", "title": "Got it"}]
    restored = NotificationPayload.from_dict(
        make_payload().to_dict() | {"actions": actions}
    )
    assert restored.actions == actions


def test_payload_roundtrip_preserves_persons() -> None:
    """Queued payloads keep the persons filter across serialize/deserialize."""
    restored = NotificationPayload.from_dict(
        make_payload(persons=["person.alice"]).to_dict()
    )
    assert restored.persons == ["person.alice"]


def test_payload_from_dict_without_persons_is_none() -> None:
    """Legacy queue entries without persons target everyone configured."""
    data = make_payload().to_dict()
    data.pop("persons", None)
    restored = NotificationPayload.from_dict(data)
    assert restored.persons is None


def test_payload_from_dict_ignores_legacy_template_field() -> None:
    """Stored template keys from old queue entries are ignored."""
    data = make_payload().to_dict()
    data["template"] = "{{ states.person | list }}"
    restored = NotificationPayload.from_dict(data)
    assert not hasattr(restored, "template")


def test_payload_from_dict_keeps_stored_strategy() -> None:
    """Queue entries keep the strategy name they were stored with."""
    data = make_payload().to_dict()
    data["strategy"] = "first_home"
    restored = NotificationPayload.from_dict(data)
    assert restored.strategy == "first_home"


def test_queued_notification_from_dict_follows_payload_strategy() -> None:
    """Queue entries keep the stored strategy name on the item and payload."""
    payload_data = make_payload().to_dict()
    payload_data["strategy"] = "first_home"
    restored = QueuedNotification.from_dict({
        "id": payload_data["id"],
        "payload": payload_data,
        "status": "pending",
    })
    assert restored.strategy == "first_home"
    assert restored.payload.strategy == "first_home"


def test_strategy_params_returns_tolerance() -> None:
    """Strategy params expose the payload tolerance."""
    payload = make_payload(tolerance=250)
    assert payload.strategy_params == {"tolerance": 250}


def test_queued_notification_roundtrip() -> None:
    """Queued notifications survive serialize/deserialize."""
    payload = make_payload("roundtrip", strategy="arrival")
    original = QueuedNotification(id="roundtrip", payload=payload, status="pending")
    restored = QueuedNotification.from_dict(original.to_dict())
    assert restored == original
