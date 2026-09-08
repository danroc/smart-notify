"""Tests for utility helpers."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State

from custom_components.smart_notify.const import (
    STRATEGIES_QUEUE_BY_DEFAULT,
    STRATEGY_CHOICES,
    STRATEGY_LABELS,
)
from custom_components.smart_notify.util import is_eligible_person, parse_duration


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2h", timedelta(hours=2)),
        ("30m", timedelta(minutes=30)),
    ],
)
def test_parse_duration(value: str, expected: timedelta) -> None:
    """Parse shorthand durations."""
    assert parse_duration(value) == expected


def test_parse_duration_invalid() -> None:
    """Reject invalid durations."""
    with pytest.raises(ValueError, match="Invalid duration"):
        parse_duration("bad")


def test_is_eligible_person() -> None:
    """Validate person eligibility."""
    assert is_eligible_person(State("person.alice", "home"))
    assert not is_eligible_person(None)
    assert not is_eligible_person(State("person.alice", STATE_UNAVAILABLE))
    assert not is_eligible_person(State("person.alice", STATE_UNKNOWN))


def test_queue_by_default_strategies() -> None:
    """Arrival, closest, and departure wait; snapshot strategies do not."""
    assert frozenset({"arrival", "closest", "departure"}) == STRATEGIES_QUEUE_BY_DEFAULT
    assert set(STRATEGY_CHOICES) >= STRATEGIES_QUEUE_BY_DEFAULT


def test_strategy_labels_cover_choices() -> None:
    """Config UI labels exist for every strategy choice."""
    assert list(STRATEGY_LABELS) == list(STRATEGY_CHOICES)
    assert all(label[0].isupper() for label in STRATEGY_LABELS.values())
