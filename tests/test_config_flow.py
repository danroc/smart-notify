"""Tests for config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smart_notify.const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    CONF_PERSONS,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


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
