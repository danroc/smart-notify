"""Everyone home strategy."""

from __future__ import annotations

from ..const import HOME_STATES, STRATEGY_EVERYONE_HOME
from .base import Strategy, StrategyContext, register_strategy


@register_strategy
class EveryoneHomeStrategy(Strategy):
    """Notify eligible persons currently at home."""

    name = STRATEGY_EVERYONE_HOME

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return persons at home."""
        return [
            state.entity_id for state in context.persons if state.state in HOME_STATES
        ]
