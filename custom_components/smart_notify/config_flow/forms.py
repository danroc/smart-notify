"""Config flow form schemas."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from ..const import CONF_PERSONS
from ..schema import defaults_schema_fields, notify_selector, person_selector


def _persons_schema(default_persons: list[str] | None = None) -> vol.Schema:
    """Return schema for selecting persons."""
    return vol.Schema({
        vol.Required(
            CONF_PERSONS,
            default=default_persons or [],
        ): person_selector(),
    })


def _user_schema() -> vol.Schema:
    """Return the user step schema."""
    return vol.Schema({
        vol.Required(CONF_PERSONS): person_selector(),
        **defaults_schema_fields(),
    })


def _person_notify_fields(
    persons: list[str],
    defaults: Mapping[str, list[str]] | None = None,
) -> dict[vol.Marker, Any]:
    """Return schema fields mapping persons to notify targets."""
    defaults = defaults or {}
    return {
        vol.Optional(person, default=defaults.get(person, [])): notify_selector()
        for person in persons
    }


def _person_services_schema(
    persons: list[str],
    defaults: Mapping[str, list[str]] | None = None,
) -> vol.Schema:
    """Return schema for mapping persons to notify services."""
    return vol.Schema(_person_notify_fields(persons, defaults))


def _build_person_services(
    persons: list[str],
    source: Mapping[str, Any],
) -> dict[str, list[str]]:
    """Return person -> notify entities mapping from form-style input."""
    return {person: list(source.get(person, [])) for person in persons}
