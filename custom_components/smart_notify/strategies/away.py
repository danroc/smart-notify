"""Away strategy."""

from __future__ import annotations

from ..const import HOME_STATES, STRATEGY_AWAY
from .base import Strategy, StrategyContext, register_strategy


@register_strategy
class AwayStrategy(Strategy):
    """Notify eligible persons currently away."""

    name = STRATEGY_AWAY

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return persons away from home (including named zones)."""
        return [
            state.entity_id
            for state in context.persons
            if state.state not in HOME_STATES
        ]
