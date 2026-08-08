"""Tests for recipient strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from custom_components.smart_notify.strategies import registry
from custom_components.smart_notify.strategies.base import StrategyContext
from custom_components.smart_notify.strategies.closest import ClosestStrategy
from custom_components.smart_notify.strategies.everyone_away import EveryoneAwayStrategy
from custom_components.smart_notify.strategies.everyone_home import EveryoneHomeStrategy
from custom_components.smart_notify.strategies.first_home import FirstHomeStrategy
from tests.conftest import make_person

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def hass(mock_hass: MagicMock) -> MagicMock:
    """Alias fixture for strategy tests."""
    return mock_hass


def test_strategy_registry_contains_all_strategies() -> None:
    """Ensure all strategies are registered."""
    names = registry.names()
    assert "everyone" in names
    assert "everyone_home" in names
    assert "everyone_away" in names
    assert "closest" in names
    assert "closest_with_tolerance" not in names
    assert "first_home" in names
    assert "template" in names


def test_closest_tolerance_zero_selects_min_distance_only(hass: MagicMock) -> None:
    """Tolerance 0 returns only person(s) at the minimum distance."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={"tolerance": 0})
    recipients = ClosestStrategy().select_recipients(context)
    assert recipients == ["person.alice"]


def test_closest_tolerance_band(hass: MagicMock) -> None:
    """Closest strategy band selects everyone within tolerance of min distance."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.8604, 2.3522),
        make_person("person.charlie", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={"tolerance": 500})
    recipients = ClosestStrategy().select_recipients(context)
    assert "person.alice" in recipients
    assert "person.bob" in recipients
    assert "person.charlie" not in recipients


def test_closest_omitted_tolerance_defaults_to_500(hass: MagicMock) -> None:
    """Omitted tolerance defaults to DEFAULT_TOLERANCE (500 m) for closest band."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.8604, 2.3522),
        make_person("person.charlie", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={})
    recipients = ClosestStrategy().select_recipients(context)
    assert "person.alice" in recipients
    assert "person.bob" in recipients
    assert "person.charlie" not in recipients


def test_closest_tolerance_zero_includes_ties(hass: MagicMock) -> None:
    """People at the same minimum distance are all selected."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.8600, 2.3522),
        make_person("person.charlie", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={"tolerance": 0})
    recipients = ClosestStrategy().select_recipients(context)
    assert set(recipients) == {"person.alice", "person.bob"}


def test_everyone_home(hass: MagicMock) -> None:
    """Select only people at home."""
    persons = [
        make_person("person.alice", "home", 48.8566, 2.3522),
        make_person("person.bob", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={})
    recipients = EveryoneHomeStrategy().select_recipients(context)
    assert recipients == ["person.alice"]


def test_first_home_when_away(hass: MagicMock) -> None:
    """Queue when nobody is home."""
    persons = [make_person("person.alice", "not_home", 48.9000, 2.3522)]
    context = StrategyContext(hass=hass, persons=persons, params={})
    recipients = FirstHomeStrategy().select_recipients(context)
    assert recipients == []


def test_everyone_away_includes_zone_states(hass: MagicMock) -> None:
    """Persons in named zones count as away from home."""
    persons = [
        make_person("person.alice", "Work", 48.9000, 2.3522),
        make_person("person.bob", "home", 48.8566, 2.3522),
        make_person("person.carol", "not_home", 48.9100, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={})
    recipients = EveryoneAwayStrategy().select_recipients(context)
    assert recipients == ["person.alice", "person.carol"]
