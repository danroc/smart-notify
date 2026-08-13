"""Home strategy."""

from __future__ import annotations

from ..const import STRATEGY_HOME
from .base import Strategy, StrategyContext, recipients_at_home, register_strategy


@register_strategy
class HomeStrategy(Strategy):
    """Notify eligible persons currently at home."""

    name = STRATEGY_HOME

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return persons at home."""
        return recipients_at_home(context)
