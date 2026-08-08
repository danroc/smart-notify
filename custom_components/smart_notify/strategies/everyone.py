"""Everyone strategy."""

from __future__ import annotations

from ..const import STRATEGY_EVERYONE
from .base import Strategy, StrategyContext, register_strategy


@register_strategy
class EveryoneStrategy(Strategy):
    """Notify every configured eligible person."""

    name = STRATEGY_EVERYONE

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return all eligible persons."""
        return [state.entity_id for state in context.persons]
