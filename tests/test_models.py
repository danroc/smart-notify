"""Tests for notification payload serialization."""

from __future__ import annotations

from homeassistant.util import dt as dt_util

from custom_components.smart_notify.models import (
    NotificationPayload,
    QueuedNotification,
    SmartNotifyConfig,
)


def _payload(persons: list[str] | None = None) -> NotificationPayload:
    now = dt_util.utcnow()
    return NotificationPayload(
        id="payload-test",
        title="Title",
        message="Message",
        strategy="direct",
        priority="normal",
        tag=None,
        payload={},
        created=now,
        expires=now,
        metadata={},
        persons=persons,
    )


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


def test_payload_from_dict_queue_default_follows_strategy() -> None:
    """Legacy queue entries without the flag follow the strategy default."""
    data = _payload().to_dict()
    data.pop("queue_if_no_candidate", None)
    assert NotificationPayload.from_dict(data).queue_if_no_candidate is False

    data["strategy"] = "home"
    assert NotificationPayload.from_dict(data).queue_if_no_candidate is False

    data["strategy"] = "arrival"
    assert NotificationPayload.from_dict(data).queue_if_no_candidate is True

    data["strategy"] = "closest"
    assert NotificationPayload.from_dict(data).queue_if_no_candidate is True


def test_payload_from_dict_normalizes_legacy_strategy() -> None:
    """Stored everyone/first_home names map to the renamed strategies."""
    data = _payload().to_dict()
    data["strategy"] = "first_home"
    restored = NotificationPayload.from_dict(data)
    assert restored.strategy == "arrival"


def test_config_maps_legacy_default_strategy() -> None:
    """Config entries that still store everyone use direct at runtime."""
    config = SmartNotifyConfig.from_entry_data({
        "persons": ["person.alice"],
        "person_services": {},
        "default_strategy": "everyone",
    })
    assert config.default_strategy == "direct"


def test_queued_notification_from_dict_follows_payload_strategy() -> None:
    """Queue entries store one strategy; aliases are applied via the payload."""
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
    assert restored.strategy == "arrival"
    assert restored.payload.strategy == "arrival"
