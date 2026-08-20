"""Smart Notify options flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from ..const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    CONF_PERSON_SERVICES,
    CONF_PERSONS,
)
from ..schema import defaults_schema_fields
from .forms import _build_person_services, _person_notify_fields

_OPTION_DEFAULT_KEYS = (
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_LOG_LEVEL,
)


class SmartNotifyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Smart Notify options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            data = dict(self.config_entry.data)
            persons = list(self.config_entry.data.get(CONF_PERSONS, []))
            person_services = _build_person_services(persons, user_input)
            defaults = {
                key: user_input[key]
                for key in _OPTION_DEFAULT_KEYS
                if key in user_input
            }
            data.update(defaults)
            data[CONF_PERSON_SERVICES] = person_services
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title="", data={})

        persons = self.config_entry.data.get(CONF_PERSONS, [])
        person_services = self.config_entry.data.get(CONF_PERSON_SERVICES, {})
        schema_dict: dict[vol.Marker, Any] = {
            **defaults_schema_fields(self.config_entry.data),
            **_person_notify_fields(persons, person_services),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
