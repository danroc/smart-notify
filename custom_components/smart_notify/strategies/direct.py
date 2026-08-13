"""Direct strategy."""

from __future__ import annotations

from ..const import STRATEGY_DIRECT
from .base import Strategy, StrategyContext, register_strategy


@register_strategy
class DirectStrategy(Strategy):
    """Notify every configured eligible person."""

    name = STRATEGY_DIRECT

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return all eligible persons."""
        return [state.entity_id for state in context.persons]
