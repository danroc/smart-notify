"""Sensor platform for Smart Notify."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_DELIVERED_TODAY, SENSOR_FAILED_TODAY, SENSOR_PENDING
from .coordinator import SmartNotifyCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Notify sensors."""
    coordinator: SmartNotifyCoordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities([
        SmartNotifyPendingSensor(coordinator, entry),
        SmartNotifyDeliveredTodaySensor(coordinator, entry),
        SmartNotifyFailedTodaySensor(coordinator, entry),
    ])


class SmartNotifySensor(CoordinatorEntity[SmartNotifyCoordinator], SensorEntity):
    """Base Smart Notify diagnostic sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartNotifyCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        name: str,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Notify",
            "manufacturer": "Smart Notify",
            "model": "Notification Router",
        }


class SmartNotifyPendingSensor(SmartNotifySensor):
    """Pending notification count."""

    def __init__(self, coordinator: SmartNotifyCoordinator, entry: ConfigEntry) -> None:
        """Initialize pending sensor."""
        super().__init__(coordinator, entry, SENSOR_PENDING, "Pending")

    @property
    def native_value(self) -> int:
        """Pending notification count."""
        return self.coordinator.pending_count()


class SmartNotifyDeliveredTodaySensor(SmartNotifySensor):
    """Delivered today count."""

    def __init__(self, coordinator: SmartNotifyCoordinator, entry: ConfigEntry) -> None:
        """Initialize delivered sensor."""
        super().__init__(coordinator, entry, SENSOR_DELIVERED_TODAY, "Delivered today")

    @property
    def native_value(self) -> int:
        """Deliveries completed today."""
        return self.coordinator.delivered_today()


class SmartNotifyFailedTodaySensor(SmartNotifySensor):
    """Failed today count."""

    def __init__(self, coordinator: SmartNotifyCoordinator, entry: ConfigEntry) -> None:
        """Initialize failed sensor."""
        super().__init__(coordinator, entry, SENSOR_FAILED_TODAY, "Failed today")

    @property
    def native_value(self) -> int:
        """Failed deliveries today."""
        return self.coordinator.failed_today()
