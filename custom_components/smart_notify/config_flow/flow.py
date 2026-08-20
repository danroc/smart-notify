"""Smart Notify config flow."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback

from ..const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    CONF_PERSON_SERVICES,
    CONF_PERSONS,
    DOMAIN,
)
from .forms import (
    _build_person_services,
    _person_services_schema,
    _persons_schema,
    _user_schema,
)
from .options import SmartNotifyOptionsFlowHandler


class SmartNotifyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Notify."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            persons = list(user_input[CONF_PERSONS])
            if not persons:
                errors["base"] = "persons_required"
            else:
                self._persons = persons
                self._person_services_defaults = None
                self._reconfigure_entry = None
                self._defaults = {
                    CONF_DEFAULT_STRATEGY: user_input[CONF_DEFAULT_STRATEGY],
                    CONF_DEFAULT_TOLERANCE: user_input[CONF_DEFAULT_TOLERANCE],
                    CONF_DEFAULT_EXPIRE_AFTER: user_input[CONF_DEFAULT_EXPIRE_AFTER],
                    CONF_ARRIVAL_DEBOUNCE_SECONDS: int(
                        user_input[CONF_ARRIVAL_DEBOUNCE_SECONDS]
                    ),
                    CONF_LOG_LEVEL: user_input[CONF_LOG_LEVEL],
                }
                return await self.async_step_person_services()

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add or remove persons on an existing installation."""
        reconfigure_entry = self._get_reconfigure_entry()
        if reconfigure_entry is None:
            return self.async_abort(reason="entry_not_found")

        errors: dict[str, str] = {}
        if user_input is not None:
            persons = list(user_input[CONF_PERSONS])
            if not persons:
                errors["base"] = "persons_required"
            else:
                self._persons = persons
                self._reconfigure_entry = reconfigure_entry
                existing_services = reconfigure_entry.data.get(CONF_PERSON_SERVICES, {})
                self._person_services_defaults = _build_person_services(
                    self._persons,
                    existing_services,
                )
                return await self.async_step_person_services()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_persons_schema(reconfigure_entry.data.get(CONF_PERSONS, [])),
            errors=errors,
        )

    async def async_step_person_services(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Map notify services to persons."""
        if user_input is not None:
            person_services = _build_person_services(self._persons, user_input)
            if self._reconfigure_entry is not None:
                data = dict(self._reconfigure_entry.data)
                data[CONF_PERSONS] = self._persons
                data[CONF_PERSON_SERVICES] = person_services
                return self.async_update_reload_and_abort(
                    self._reconfigure_entry,
                    data=data,
                )

            return self.async_create_entry(
                title="Smart Notify",
                data={
                    CONF_PERSONS: self._persons,
                    CONF_PERSON_SERVICES: person_services,
                    **self._defaults,
                },
            )

        return self.async_show_form(
            step_id="person_services",
            data_schema=_person_services_schema(
                self._persons,
                self._person_services_defaults,
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SmartNotifyOptionsFlowHandler:
        """Get the options flow."""
        del config_entry
        return SmartNotifyOptionsFlowHandler()
