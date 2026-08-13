"""Tests for utility helpers."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State
from homeassistant.util import dt as dt_util

from custom_components.smart_notify.const import (
    STRATEGY_CHOICES,
    STRATEGY_LABELS,
)
from custom_components.smart_notify.util import (
    default_queue_if_no_candidate,
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


def test_default_queue_if_no_candidate() -> None:
    """Arrival and closest wait; snapshot strategies drop."""
    assert default_queue_if_no_candidate("arrival") is True
    assert default_queue_if_no_candidate("closest") is True
    assert default_queue_if_no_candidate("direct") is False
    assert default_queue_if_no_candidate("home") is False
    assert default_queue_if_no_candidate("away") is False


def test_strategy_labels_cover_choices() -> None:
    """Config UI labels exist for every strategy choice."""
    assert list(STRATEGY_LABELS) == list(STRATEGY_CHOICES)
    assert all(label[0].isupper() for label in STRATEGY_LABELS.values())


def test_services_yaml_strategy_labels_match_const() -> None:
    """services.yaml strategy dropdown stays in sync with STRATEGY_LABELS."""
    path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "smart_notify"
        / "services.yaml"
    )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    options = data["send"]["fields"]["strategy"]["selector"]["select"]["options"]
    assert {option["value"]: option["label"] for option in options} == STRATEGY_LABELS
