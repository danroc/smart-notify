"""Departure strategy."""

from __future__ import annotations

from ..const import STRATEGY_DEPARTURE
from .away import AwayStrategy
from .base import register_strategy


@register_strategy
class DepartureStrategy(AwayStrategy):
    """Deliver immediately to people away, otherwise queue until someone leaves."""

    name = STRATEGY_DEPARTURE
