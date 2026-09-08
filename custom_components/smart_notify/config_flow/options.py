"""Smart Notify options flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from ..const import CONF_PERSON_SERVICES, CONF_PERSONS
from ..schema import defaults_schema_fields
from .forms import _build_person_services, _person_notify_fields


class SmartNotifyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Smart Notify options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        current = dict(self.config_entry.data)
        persons = list(current.get(CONF_PERSONS, []))

        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({
                    **defaults_schema_fields(current),
                    **_person_notify_fields(
                        persons, current.get(CONF_PERSON_SERVICES, {})
                    ),
                }),
            )

        person_ids = set(persons)
        current.update(
            (key, value) for key, value in user_input.items() if key not in person_ids
        )
        current[CONF_PERSON_SERVICES] = _build_person_services(persons, user_input)
        self.hass.config_entries.async_update_entry(self.config_entry, data=current)
        return self.async_create_entry(title="", data={})
