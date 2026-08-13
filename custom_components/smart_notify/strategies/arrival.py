"""Arrival strategy."""

from __future__ import annotations

from ..const import STRATEGY_ARRIVAL
from .base import Strategy, StrategyContext, recipients_at_home, register_strategy


@register_strategy
class ArrivalStrategy(Strategy):
    """Deliver immediately to people at home, otherwise queue until someone arrives."""

    name = STRATEGY_ARRIVAL

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return persons at home when anyone is home."""
        return recipients_at_home(context)
