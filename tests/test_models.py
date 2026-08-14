"""Tests for notification payload serialization."""

from __future__ import annotations

from homeassistant.util import dt as dt_util

from custom_components.smart_notify.models import (
    NotificationPayload,
    QueuedNotification,
)


def _payload(persons: list[str] | None = None) -> NotificationPayload:
    now = dt_util.utcnow()
    return NotificationPayload(
        id="payload-test",
        title="Title",
        message="Message",
        strategy="direct",
        tag=None,
        payload={},
        created=now,
        expires=now,
        persons=persons,
    )


def test_payload_roundtrip_preserves_actions() -> None:
    """Queued payloads keep actions across serialize/deserialize."""
    actions = [{"action": "ACK", "title": "Got it"}]
    restored = NotificationPayload.from_dict(
        _payload().to_dict() | {"actions": actions}
    )
    assert restored.actions == actions


def test_payload_roundtrip_preserves_persons() -> None:
    """Queued payloads keep the persons filter across serialize/deserialize."""
    restored = NotificationPayload.from_dict(
        _payload(persons=["person.alice"]).to_dict()
    )
    assert restored.persons == ["person.alice"]


def test_payload_from_dict_without_persons_is_none() -> None:
    """Legacy queue entries without persons target everyone configured."""
    data = _payload().to_dict()
    data.pop("persons", None)
    restored = NotificationPayload.from_dict(data)
    assert restored.persons is None


def test_payload_from_dict_ignores_legacy_template_field() -> None:
    """Stored template keys from old queue entries are ignored."""
    data = _payload().to_dict()
    data["template"] = "{{ states.person | list }}"
    restored = NotificationPayload.from_dict(data)
    assert not hasattr(restored, "template")


def test_payload_from_dict_keeps_stored_strategy() -> None:
    """Queue entries keep the strategy name they were stored with."""
    data = _payload().to_dict()
    data["strategy"] = "first_home"
    restored = NotificationPayload.from_dict(data)
    assert restored.strategy == "first_home"


def test_queued_notification_from_dict_follows_payload_strategy() -> None:
    """Queue entries keep the stored strategy name on the item and payload."""
    payload_data = _payload().to_dict()
    payload_data["strategy"] = "first_home"
    restored = QueuedNotification.from_dict({
        "id": payload_data["id"],
        "created": payload_data["created"],
        "expires": payload_data["expires"],
        "strategy": "first_home",
        "payload": payload_data,
        "status": "pending",
        "delivery_attempts": 0,
    })
    assert restored.strategy == "first_home"
    assert restored.payload.strategy == "first_home"
