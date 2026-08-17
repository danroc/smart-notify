"""Tests for config flow."""

from __future__ import annotations

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smart_notify.const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    CONF_PERSON_SERVICES,
    CONF_PERSONS,
    DOMAIN,
)
from tests.conftest import make_config_entry


def _schema_defaults(schema: vol.Schema) -> dict[str, list[str]]:
    """Return default notify mappings from a person_services form schema."""
    return {
        key.schema: key.default() if callable(key.default) else key.default
        for key in schema.schema
    }


@pytest.mark.asyncio
async def test_config_flow_user_step(hass: HomeAssistant) -> None:
    """Config flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PERSONS: ["person.alice"],
            CONF_DEFAULT_STRATEGY: "closest",
            CONF_DEFAULT_TOLERANCE: 500,
            CONF_DEFAULT_EXPIRE_AFTER: "4h",
            CONF_ARRIVAL_DEBOUNCE_SECONDS: 30,
            CONF_LOG_LEVEL: "info",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "person_services"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"person.alice": ["notify.mobile_app_alice"]},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PERSONS] == ["person.alice"]


@pytest.mark.asyncio
async def test_config_flow_reconfigure_adds_person(hass: HomeAssistant) -> None:
    """Reconfigure flow adds a person and preserves existing mappings."""
    entry = make_config_entry(
        persons=["person.alice"],
        person_services={"person.alice": ["notify.mobile_app_alice"]},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PERSONS: ["person.alice", "person.bob"]},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "person_services"
    schema = result["data_schema"]
    assert schema is not None
    assert _schema_defaults(schema) == {
        "person.alice": ["notify.mobile_app_alice"],
        "person.bob": [],
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "person.alice": ["notify.mobile_app_alice"],
            "person.bob": ["notify.mobile_app_bob"],
        },
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert entry.data[CONF_PERSONS] == ["person.alice", "person.bob"]
    assert entry.data[CONF_PERSON_SERVICES] == {
        "person.alice": ["notify.mobile_app_alice"],
        "person.bob": ["notify.mobile_app_bob"],
    }
    assert entry.data[CONF_DEFAULT_STRATEGY] == "direct"
    assert entry.data[CONF_DEFAULT_TOLERANCE] == 500
    assert entry.data[CONF_DEFAULT_EXPIRE_AFTER] == "4h"
    assert entry.data[CONF_LOG_LEVEL] == "info"


@pytest.mark.asyncio
async def test_config_flow_reconfigure_removes_person(hass: HomeAssistant) -> None:
    """Reconfigure flow drops removed persons from mappings."""
    entry = make_config_entry(
        persons=["person.alice", "person.bob"],
        person_services={
            "person.alice": ["notify.mobile_app_alice"],
            "person.bob": ["notify.mobile_app_bob"],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PERSONS: ["person.alice"]},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"person.alice": ["notify.mobile_app_alice"]},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert entry.data[CONF_PERSONS] == ["person.alice"]
    assert entry.data[CONF_PERSON_SERVICES] == {
        "person.alice": ["notify.mobile_app_alice"],
    }


@pytest.mark.asyncio
async def test_config_flow_reconfigure_requires_person(hass: HomeAssistant) -> None:
    """Reconfigure flow rejects an empty person list."""
    entry = make_config_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PERSONS: []},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    errors = result["errors"]
    assert errors is not None
    assert errors["base"] == "persons_required"
