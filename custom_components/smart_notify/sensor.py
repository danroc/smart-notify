"""Sensor platform for Smart Notify."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_DELIVERED_TODAY, SENSOR_FAILED_TODAY, SENSOR_PENDING
from .coordinator import SmartNotifyCoordinator

SensorValueFn = Callable[[SmartNotifyCoordinator], int]

_SENSOR_DEFINITIONS: tuple[tuple[str, str, SensorValueFn], ...] = (
    (SENSOR_PENDING, "Pending", lambda coordinator: coordinator.pending_count()),
    (
        SENSOR_DELIVERED_TODAY,
        "Delivered today",
        lambda coordinator: coordinator.delivered_today(),
    ),
    (
        SENSOR_FAILED_TODAY,
        "Failed today",
        lambda coordinator: coordinator.failed_today(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Notify sensors."""
    coordinator: SmartNotifyCoordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities([
        SmartNotifySensor(coordinator, entry, sensor_type, name, value_fn)
        for sensor_type, name, value_fn in _SENSOR_DEFINITIONS
    ])


class SmartNotifySensor(CoordinatorEntity[SmartNotifyCoordinator], SensorEntity):
    """Smart Notify diagnostic sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartNotifyCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        name: str,
        value_fn: SensorValueFn,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._value_fn = value_fn
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Notify",
            "manufacturer": "Smart Notify",
            "model": "Notification Router",
        }

    @property
    def native_value(self) -> int:
        """Current sensor value."""
        return self._value_fn(self.coordinator)
