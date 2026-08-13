"""Tests for notification payload serialization."""

from __future__ import annotations

from homeassistant.util import dt as dt_util

from custom_components.smart_notify.models import NotificationPayload


def _payload(persons: list[str] | None = None) -> NotificationPayload:
    now = dt_util.utcnow()
    return NotificationPayload(
        id="payload-test",
        title="Title",
        message="Message",
        strategy="everyone",
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
