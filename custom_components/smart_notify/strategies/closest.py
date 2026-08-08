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
        raw = context.params.get("tolerance", DEFAULT_TOLERANCE)
        tolerance = int(DEFAULT_TOLERANCE if raw is None else raw)
        distances: list[tuple[str, float]] = []
        for state in context.persons:
            distance = distance_to_home_meters(context.hass, state)
            if distance is None:
                continue
            distances.append((state.entity_id, distance))
            _LOGGER.debug("Distance for %s: %.1f m", state.entity_id, distance)

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
