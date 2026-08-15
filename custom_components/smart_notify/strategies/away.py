"""Away strategy."""

from __future__ import annotations

from ..const import STRATEGY_AWAY
from .base import Strategy, StrategyContext, recipients_away, register_strategy


@register_strategy
class AwayStrategy(Strategy):
    """Notify eligible persons currently away."""

    name = STRATEGY_AWAY

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return persons away from home (including named zones)."""
        return recipients_away(context)
