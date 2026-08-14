"""Arrival strategy."""

from __future__ import annotations

from ..const import STRATEGY_ARRIVAL
from .base import register_strategy
from .home import HomeStrategy


@register_strategy
class ArrivalStrategy(HomeStrategy):
    """Deliver immediately to people at home, otherwise queue until someone arrives."""

    name = STRATEGY_ARRIVAL
