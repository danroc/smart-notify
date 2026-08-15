"""Strategy base classes and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from homeassistant.core import HomeAssistant, State

from ..const import HOME_STATES


@dataclass(slots=True)
class StrategyContext:
    """Context passed to recipient strategies."""

    hass: HomeAssistant
    persons: list[State]
    params: dict[str, Any] = field(default_factory=dict)


def recipients_at_home(context: StrategyContext) -> list[str]:
    """Return person entity IDs currently at home."""
    return [state.entity_id for state in context.persons if state.state in HOME_STATES]


def recipients_away(context: StrategyContext) -> list[str]:
    """Return person entity IDs currently away from home."""
    return [
        state.entity_id
        for state in context.persons
        if state.state not in HOME_STATES
    ]


class Strategy(ABC):
    """Abstract recipient selection strategy."""

    name: ClassVar[str]

    @abstractmethod
    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return person entity IDs that should receive the notification."""


class StrategyRegistry:
    """Registry for recipient strategies."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._strategies: dict[str, type[Strategy]] = {}

    def register[TStrategy: Strategy](
        self, strategy_cls: type[TStrategy]
    ) -> type[TStrategy]:
        """Register a strategy class."""
        self._strategies[strategy_cls.name] = strategy_cls
        return strategy_cls

    def get(self, name: str) -> Strategy:
        """Return a strategy instance by name."""
        if name not in self._strategies:
            msg = f"Unknown strategy: {name}"
            raise ValueError(msg)
        return self._strategies[name]()

    def names(self) -> list[str]:
        """Return registered strategy names."""
        return sorted(self._strategies)


registry = StrategyRegistry()


def register_strategy[TStrategy: Strategy](
    strategy_cls: type[TStrategy],
) -> type[TStrategy]:
    """Decorator to register a strategy implementation."""
    return registry.register(strategy_cls)
