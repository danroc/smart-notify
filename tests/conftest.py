"""Test helpers for Smart Notify."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_notify.const import DOMAIN
from custom_components.smart_notify.models import NotificationPayload

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def enable_custom_integrations_autouse(enable_custom_integrations: object) -> None:
    """Load custom components from this repository in every test."""


def make_person(
    entity_id: str,
    state: str,
    latitude: float,
    longitude: float,
) -> State:
    """Create a person state for tests."""
    return State(
        entity_id,
        state,
        {
            ATTR_LATITUDE: latitude,
            ATTR_LONGITUDE: longitude,
        },
    )


def make_payload(
    notification_id: str = "test-payload",
    *,
    expires_delta: timedelta | None = None,
    **overrides: object,
) -> NotificationPayload:
    """Build a notification payload with overridable defaults."""
    now = dt_util.utcnow()
    base = NotificationPayload(
        id=notification_id,
        title="Title",
        message="Message",
        strategy="direct",
        tag=None,
        level="normal",
        group=None,
        image=None,
        url=None,
        created=now,
        expires=now + (expires_delta or timedelta()),
        actions=None,
    )
    return replace(base, **overrides) if overrides else base


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mocked Home Assistant instance."""
    mock = MagicMock()
    mock.config.latitude = 48.8566
    mock.config.longitude = 2.3522
    return mock


@pytest.fixture
async def smart_notify_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and set up a Smart Notify config entry."""
    return await setup_integration(
        hass,
        persons=["person.alice"],
        person_services={"person.alice": ["notify.mobile_app_alice"]},
        default_strategy="closest",
    )


def make_config_entry(**overrides: object) -> MockConfigEntry:
    """Build a Smart Notify config entry with overridable defaults."""
    data: dict[str, object] = {
        "persons": ["person.alice", "person.bob"],
        "person_services": {
            "person.alice": ["notify.mobile_app_alice"],
            "person.bob": ["notify.mobile_app_bob"],
        },
        "default_strategy": "direct",
        "default_tolerance": 500,
        "default_expire_after": "4h",
        "log_level": "info",
    }
    data.update(overrides)
    return MockConfigEntry(domain=DOMAIN, data=data)


async def setup_integration(
    hass: HomeAssistant,
    **overrides: object,
) -> MockConfigEntry:
    """Add and set up a Smart Notify config entry for integration tests."""
    entry = make_config_entry(**overrides)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def set_person_home(hass: HomeAssistant, entity_id: str) -> None:
    """Set a person state to home at Home Assistant base coordinates."""
    hass.states.async_set(
        entity_id,
        "home",
        {"latitude": hass.config.latitude, "longitude": hass.config.longitude},
    )


def set_person_away(
    hass: HomeAssistant,
    entity_id: str,
    *,
    state: str = "not_home",
    latitude: float = 40.0,
    longitude: float = -74.0,
) -> None:
    """Set a person state away from home with explicit coordinates."""
    hass.states.async_set(
        entity_id,
        state,
        {"latitude": latitude, "longitude": longitude},
    )
