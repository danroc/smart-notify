"""Voluptuous validators for Smart Notify."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from ..const import LEVEL_CHOICES, LOG_LEVELS, STRATEGY_CHOICES
from ..util import parse_duration

ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("action"): cv.string,
        vol.Required("title"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

CV_STRATEGY = vol.In(STRATEGY_CHOICES)
CV_LEVEL = vol.In(LEVEL_CHOICES)
CV_TOLERANCE = cv.positive_int
CV_LOG_LEVEL = vol.In(LOG_LEVELS)
CV_ACTIONS = vol.All(cv.ensure_list, [ACTION_SCHEMA])
CV_PERSONS = vol.All(
    cv.ensure_list,
    [vol.All(cv.entity_id, cv.entity_domain("person"))],
    vol.Length(min=1),
)


def cv_duration(value: object) -> str:
    """Validate duration shorthand such as 4h, 30m, or 1d."""
    if not isinstance(value, str):
        msg = "expected a duration string"
        raise vol.Invalid(msg)
    try:
        parse_duration(value)
    except ValueError as err:
        raise vol.Invalid(str(err)) from err
    return value
