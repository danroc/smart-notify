"""Tests for recipient resolution with an optional persons filter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_notify.recipient import RecipientResolver
from tests.conftest import make_person

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from homeassistant.core import State


def _resolver_with_people(
    hass: MagicMock,
    people: dict[str, State],
) -> RecipientResolver:
    """Build a resolver whose hass.states.get returns the given people."""
    hass.states.get.side_effect = people.get
    return RecipientResolver(hass, list(people))


def test_resolve_without_persons_uses_all_configured(mock_hass: MagicMock) -> None:
    """Omitting persons passes every configured eligible person to the strategy."""
    resolver = _resolver_with_people(
        mock_hass,
        {
            "person.alice": make_person("person.alice", "home", 48.8566, 2.3522),
            "person.bob": make_person("person.bob", "home", 48.8566, 2.3522),
        },
    )
    recipients = resolver.resolve("everyone", {})
    assert recipients == ["person.alice", "person.bob"]


def test_resolve_filters_to_requested_persons(mock_hass: MagicMock) -> None:
    """A persons filter intersects with the configured roster before the strategy."""
    resolver = _resolver_with_people(
        mock_hass,
        {
            "person.alice": make_person("person.alice", "home", 48.8566, 2.3522),
            "person.bob": make_person("person.bob", "home", 48.8566, 2.3522),
        },
    )
    recipients = resolver.resolve("everyone", {}, persons=["person.alice"])
    assert recipients == ["person.alice"]


def test_resolve_drops_unconfigured_persons(mock_hass: MagicMock) -> None:
    """Entity IDs that are not in the integration config are ignored."""
    resolver = _resolver_with_people(
        mock_hass,
        {
            "person.alice": make_person("person.alice", "home", 48.8566, 2.3522),
        },
    )
    recipients = resolver.resolve(
        "everyone",
        {},
        persons=["person.alice", "person.carol"],
    )
    assert recipients == ["person.alice"]


def test_resolve_all_unconfigured_returns_empty(mock_hass: MagicMock) -> None:
    """If every requested person is unknown, the strategy sees nobody."""
    resolver = _resolver_with_people(
        mock_hass,
        {
            "person.alice": make_person("person.alice", "home", 48.8566, 2.3522),
        },
    )
    recipients = resolver.resolve("everyone", {}, persons=["person.carol"])
    assert recipients == []


def test_resolve_everyone_home_respects_filter_when_away(
    mock_hass: MagicMock,
) -> None:
    """Filtering to someone who is away yields no recipients."""
    resolver = _resolver_with_people(
        mock_hass,
        {
            "person.alice": make_person("person.alice", "not_home", 48.9, 2.35),
            "person.bob": make_person("person.bob", "home", 48.8566, 2.3522),
        },
    )
    recipients = resolver.resolve("everyone_home", {}, persons=["person.alice"])
    assert recipients == []
