"""Closest person strategy."""

from __future__ import annotations

import logging

from ..const import DEFAULT_TOLERANCE, LOGGER_NAME, STRATEGY_CLOSEST
from ..util import distance_to_home_meters
from .base import Strategy, StrategyContext, register_strategy

_LOGGER = logging.getLogger(LOGGER_NAME)


@register_strategy
class ClosestStrategy(Strategy):
    """Notify everyone within tolerance of the closest distance to home."""

    name = STRATEGY_CLOSEST

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return persons within tolerance of the closest distance."""
        raw = context.params.get("tolerance")
        tolerance = DEFAULT_TOLERANCE if raw is None else int(raw)
        distances = [
            (state.entity_id, distance)
            for state in context.persons
            if (distance := distance_to_home_meters(context.hass, state)) is not None
        ]
        if not distances:
            return []

        minimum = min(distance for _, distance in distances)
        threshold = minimum + tolerance
        recipients = [
            entity_id for entity_id, distance in distances if distance <= threshold
        ]

        _LOGGER.debug(
            "Closest distance %.1f m, tolerance %d m, recipients: %s",
            minimum,
            tolerance,
            recipients,
        )

        return recipients
