"""Strategy base classes and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import HOME_STATES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State


@dataclass(slots=True)
class StrategyContext:
    """Context passed to recipient strategies."""

    hass: HomeAssistant
    persons: list[State]
    params: dict[str, Any] = field(default_factory=dict)


def recipients_at_home(context: StrategyContext) -> list[str]:
    """Return person entity IDs currently at home."""
    return [state.entity_id for state in context.persons if state.state in HOME_STATES]


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

    def register(self, strategy_cls: type[Strategy]) -> type[Strategy]:
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


def register_strategy(strategy_cls: type[Strategy]) -> type[Strategy]:
    """Decorator to register a strategy implementation."""
    return registry.register(strategy_cls)
