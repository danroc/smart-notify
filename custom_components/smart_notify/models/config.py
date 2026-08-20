"""Integration configuration model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    CONF_PERSON_SERVICES,
    CONF_PERSONS,
    DEFAULT_ARRIVAL_DEBOUNCE_SECONDS,
    DEFAULT_EXPIRE_AFTER,
    DEFAULT_LOG_LEVEL,
    DEFAULT_STRATEGY,
    DEFAULT_TOLERANCE,
)


@dataclass(slots=True)
class SmartNotifyConfig:
    """Runtime configuration for Smart Notify."""

    persons: list[str]
    person_services: dict[str, list[str]]
    default_strategy: str = DEFAULT_STRATEGY
    default_tolerance: int = DEFAULT_TOLERANCE
    default_expire_after: str = DEFAULT_EXPIRE_AFTER
    log_level: str = DEFAULT_LOG_LEVEL
    arrival_debounce_seconds: int = DEFAULT_ARRIVAL_DEBOUNCE_SECONDS

    @classmethod
    def from_entry_data(cls, data: Mapping[str, Any]) -> SmartNotifyConfig:
        """Build configuration from a config entry."""
        return cls(
            persons=list(data.get(CONF_PERSONS, [])),
            person_services={
                key: list(value)
                for key, value in data.get(CONF_PERSON_SERVICES, {}).items()
            },
            default_strategy=data.get(CONF_DEFAULT_STRATEGY, DEFAULT_STRATEGY),
            default_tolerance=int(data.get(CONF_DEFAULT_TOLERANCE, DEFAULT_TOLERANCE)),
            default_expire_after=data.get(
                CONF_DEFAULT_EXPIRE_AFTER, DEFAULT_EXPIRE_AFTER
            ),
            log_level=data.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL),
            arrival_debounce_seconds=int(
                data.get(
                    CONF_ARRIVAL_DEBOUNCE_SECONDS, DEFAULT_ARRIVAL_DEBOUNCE_SECONDS
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration."""
        return {
            CONF_PERSONS: self.persons,
            CONF_PERSON_SERVICES: self.person_services,
            CONF_DEFAULT_STRATEGY: self.default_strategy,
            CONF_DEFAULT_TOLERANCE: self.default_tolerance,
            CONF_DEFAULT_EXPIRE_AFTER: self.default_expire_after,
            CONF_LOG_LEVEL: self.log_level,
            CONF_ARRIVAL_DEBOUNCE_SECONDS: self.arrival_debounce_seconds,
        }
