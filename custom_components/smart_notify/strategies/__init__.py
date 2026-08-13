"""Strategy package registration."""

from __future__ import annotations

from . import closest, everyone, everyone_away, everyone_home, first_home
from .base import Strategy, StrategyContext, register_strategy, registry

__all__ = [
    "Strategy",
    "StrategyContext",
    "closest",
    "everyone",
    "everyone_away",
    "everyone_home",
    "first_home",
    "register_strategy",
    "registry",
]
