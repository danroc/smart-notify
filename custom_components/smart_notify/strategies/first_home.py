"""First home strategy."""

from __future__ import annotations

from ..const import HOME_STATES, STRATEGY_FIRST_HOME
from .base import Strategy, StrategyContext, register_strategy


@register_strategy
class FirstHomeStrategy(Strategy):
    """Deliver immediately to people at home, otherwise queue."""

    name = STRATEGY_FIRST_HOME

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return persons at home when anyone is home."""
        return [
            state.entity_id for state in context.persons if state.state in HOME_STATES
        ]
