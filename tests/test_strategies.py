"""Tests for recipient strategies."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.smart_notify.strategies import registry
from custom_components.smart_notify.strategies.arrival import ArrivalStrategy
from custom_components.smart_notify.strategies.away import AwayStrategy
from custom_components.smart_notify.strategies.base import StrategyContext
from custom_components.smart_notify.strategies.closest import ClosestStrategy
from custom_components.smart_notify.strategies.departure import DepartureStrategy
from custom_components.smart_notify.strategies.direct import DirectStrategy
from custom_components.smart_notify.strategies.home import HomeStrategy
from tests.conftest import make_person


def test_strategy_registry_contains_all_strategies() -> None:
    """Ensure all strategies are registered under the single-word names."""
    assert registry.names() == [
        "arrival",
        "away",
        "closest",
        "departure",
        "direct",
        "home",
    ]


def test_closest_tolerance_zero_selects_min_distance_only(mock_hass: MagicMock) -> None:
    """Tolerance 0 returns only person(s) at the minimum distance."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=mock_hass, persons=persons, params={"tolerance": 0})
    recipients = ClosestStrategy().select_recipients(context)
    assert recipients == ["person.alice"]


@pytest.mark.parametrize("params", [{"tolerance": 500}, {}])
def test_closest_tolerance_band(mock_hass: MagicMock, params: dict[str, int]) -> None:
    """Closest band selects everyone within 500 m of the minimum distance."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.8604, 2.3522),
        make_person("person.charlie", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=mock_hass, persons=persons, params=params)
    recipients = ClosestStrategy().select_recipients(context)
    assert recipients == ["person.alice", "person.bob"]


def test_closest_tolerance_zero_includes_ties(mock_hass: MagicMock) -> None:
    """People at the same minimum distance are all selected."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.8600, 2.3522),
        make_person("person.charlie", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=mock_hass, persons=persons, params={"tolerance": 0})
    recipients = ClosestStrategy().select_recipients(context)
    assert set(recipients) == {"person.alice", "person.bob"}


def test_direct_selects_all_eligible(mock_hass: MagicMock) -> None:
    """Direct notifies every eligible person regardless of presence."""
    persons = [
        make_person("person.alice", "home", 48.8566, 2.3522),
        make_person("person.bob", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=mock_hass, persons=persons, params={})
    recipients = DirectStrategy().select_recipients(context)
    assert recipients == ["person.alice", "person.bob"]


def test_home_selects_only_people_at_home(mock_hass: MagicMock) -> None:
    """Home selects only people at home."""
    persons = [
        make_person("person.alice", "home", 48.8566, 2.3522),
        make_person("person.bob", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=mock_hass, persons=persons, params={})
    recipients = HomeStrategy().select_recipients(context)
    assert recipients == ["person.alice"]


def test_arrival_empty_when_everyone_away(mock_hass: MagicMock) -> None:
    """Arrival with nobody home returns no recipients."""
    persons = [make_person("person.alice", "not_home", 48.9000, 2.3522)]
    context = StrategyContext(hass=mock_hass, persons=persons, params={})
    recipients = ArrivalStrategy().select_recipients(context)
    assert recipients == []


def test_away_includes_zone_states(mock_hass: MagicMock) -> None:
    """Persons in named zones count as away from home."""
    persons = [
        make_person("person.alice", "Work", 48.9000, 2.3522),
        make_person("person.bob", "home", 48.8566, 2.3522),
        make_person("person.carol", "not_home", 48.9100, 2.3522),
    ]
    context = StrategyContext(hass=mock_hass, persons=persons, params={})
    recipients = AwayStrategy().select_recipients(context)
    assert recipients == ["person.alice", "person.carol"]


def test_departure_empty_when_everyone_home(mock_hass: MagicMock) -> None:
    """Departure with everyone home returns no recipients."""
    persons = [make_person("person.alice", "home", 48.8566, 2.3522)]
    context = StrategyContext(hass=mock_hass, persons=persons, params={})
    recipients = DepartureStrategy().select_recipients(context)
    assert recipients == []
