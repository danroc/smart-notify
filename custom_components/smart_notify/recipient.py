"""Recipient eligibility and strategy orchestration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .const import LOGGER_NAME
from .strategies import registry
from .strategies.base import StrategyContext
from .util import get_person_states, is_eligible_person

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State

_LOGGER = logging.getLogger(LOGGER_NAME)


class RecipientResolver:
    """Resolve notification recipients using configured strategies."""

    def __init__(self, hass: HomeAssistant, configured_persons: list[str]) -> None:
        """Initialize resolver."""
        self._hass = hass
        self._configured_persons = configured_persons

    def get_eligible_persons(self) -> list[State]:
        """Return configured persons that pass eligibility checks."""
        states = get_person_states(self._hass, self._configured_persons)
        eligible = [state for state in states if is_eligible_person(state)]
        _LOGGER.debug(
            "Eligible persons: %s",
            [state.entity_id for state in eligible],
        )
        return eligible

    def resolve(
        self,
        strategy_name: str,
        params: dict[str, Any],
        persons: list[str] | None = None,
    ) -> list[str]:
        """Resolve recipients for a strategy.

        When ``persons`` is set, only those entity IDs that are also configured
        and eligible are passed to the strategy. Unknown IDs are dropped.
        """
        eligible = self.get_eligible_persons()
        if persons is not None:
            allowed = set(persons)
            eligible = [state for state in eligible if state.entity_id in allowed]
        context = StrategyContext(
            hass=self._hass,
            persons=eligible,
            params=params,
        )
        strategy = registry.get(strategy_name)
        _LOGGER.debug("Selected strategy: %s", strategy.name)
        recipients = strategy.select_recipients(context)
        _LOGGER.debug("Strategy %s selected recipients: %s", strategy_name, recipients)
        return recipients
