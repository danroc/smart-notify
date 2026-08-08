"""Tests for utility helpers."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State
from homeassistant.util import dt as dt_util

from custom_components.smart_notify.util import (
    is_eligible_person,
    parse_duration,
    parse_expire_after,
)


def test_parse_duration_hours() -> None:
    """Parse hour durations."""
    assert parse_duration("2h") == timedelta(hours=2)


def test_parse_duration_minutes() -> None:
    """Parse minute durations."""
    assert parse_duration("30m") == timedelta(minutes=30)


def test_parse_duration_invalid() -> None:
    """Reject invalid durations."""
    with pytest.raises(ValueError, match="Invalid duration"):
        parse_duration("bad")


def test_parse_expire_after() -> None:
    """Parse expiration timestamps."""
    base = dt_util.utcnow()
    expires = parse_expire_after("1h", base)
    assert expires == base + timedelta(hours=1)


def test_is_eligible_person() -> None:
    """Validate person eligibility."""
    assert is_eligible_person(State("person.alice", "home"))
    assert not is_eligible_person(None)
    assert not is_eligible_person(State("person.alice", STATE_UNAVAILABLE))
    assert not is_eligible_person(State("person.alice", STATE_UNKNOWN))
