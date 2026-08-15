"""Config flow for Smart Notify."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    CONF_PERSON_SERVICES,
    CONF_PERSONS,
    DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
    DEFAULT_EXPIRE_AFTER,
    DEFAULT_STRATEGY,
    DEFAULT_TOLERANCE,
    DOMAIN,
    STRATEGY_CHOICES,
    STRATEGY_LABELS,
)


def _strategy_selector_options() -> list[selector.SelectOptionDict]:
    """Return labeled strategy dropdown options."""
    return [
        {"value": name, "label": STRATEGY_LABELS[name]} for name in STRATEGY_CHOICES
    ]


def _defaults_schema_fields(
    defaults: Mapping[str, Any] | None = None,
) -> dict[vol.Marker, Any]:
    """Return schema fields for integration default settings."""
    data = defaults or {}
    return {
        vol.Required(
            CONF_DEFAULT_STRATEGY,
            default=data.get(CONF_DEFAULT_STRATEGY, DEFAULT_STRATEGY),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=_strategy_selector_options()),
        ),
        vol.Required(
            CONF_DEFAULT_TOLERANCE,
            default=data.get(CONF_DEFAULT_TOLERANCE, DEFAULT_TOLERANCE),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                step=50,
                mode=selector.NumberSelectorMode.BOX,
            ),
        ),
        vol.Required(
            CONF_DEFAULT_EXPIRE_AFTER,
            default=data.get(CONF_DEFAULT_EXPIRE_AFTER, DEFAULT_EXPIRE_AFTER),
        ): selector.TextSelector(),
        vol.Required(
            CONF_ARRIVAL_DEBOUNCE_SECONDS,
            default=data.get(
                CONF_ARRIVAL_DEBOUNCE_SECONDS, DEFAULT_ARRIVAL_DEBOUNCE_SECONDS
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=600,
                step=5,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="seconds",
            ),
        ),
        vol.Required(
            CONF_LOG_LEVEL,
            default=data.get(CONF_LOG_LEVEL, "info"),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=["debug", "info", "warning"]),
        ),
    }


def _user_schema() -> vol.Schema:
    """Return the user step schema."""
    return vol.Schema({
        vol.Required(CONF_PERSONS): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="person", multiple=True),
        ),
        **_defaults_schema_fields(),
    })


def _person_notify_fields(
    persons: list[str],
    defaults: Mapping[str, list[str]] | None = None,
) -> dict[vol.Marker, Any]:
    """Return schema fields mapping persons to notify targets."""
    defaults = defaults or {}
    return {
        vol.Optional(person, default=defaults.get(person, [])): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="notify", multiple=True),
        )
        for person in persons
    }


def _person_services_schema(persons: list[str]) -> vol.Schema:
    """Return schema for mapping persons to notify services."""
    return vol.Schema(_person_notify_fields(persons))


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
            if not user_input[CONF_PERSONS]:
                errors["base"] = "persons_required"
            else:
                self._persons = user_input[CONF_PERSONS]
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

    async def async_step_person_services(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Map notify services to persons."""
        if user_input is not None:
            return self.async_create_entry(
                title="Smart Notify",
                data={
                    CONF_PERSONS: self._persons,
                    CONF_PERSON_SERVICES: user_input,
                    **self._defaults,
                },
            )

        return self.async_show_form(
            step_id="person_services",
            data_schema=_person_services_schema(self._persons),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SmartNotifyOptionsFlowHandler:
        """Get the options flow."""
        del config_entry
        return SmartNotifyOptionsFlowHandler()


class SmartNotifyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Smart Notify options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            data = dict(self.config_entry.data)
            person_services = {
                key: value
                for key, value in user_input.items()
                if key.startswith("person.")
            }
            defaults = {
                key: value
                for key, value in user_input.items()
                if not key.startswith("person.")
            }
            data.update(defaults)
            data[CONF_PERSON_SERVICES] = person_services
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title="", data={})

        persons = self.config_entry.data.get(CONF_PERSONS, [])
        person_services = self.config_entry.data.get(CONF_PERSON_SERVICES, {})
        schema_dict: dict[vol.Marker, Any] = {
            **_defaults_schema_fields(self.config_entry.data),
            **_person_notify_fields(persons, person_services),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
