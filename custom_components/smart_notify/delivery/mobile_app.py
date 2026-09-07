"""Resolve mobile app notify entities to legacy notify services."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify


def _get_device_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Return the device ID of a mobile_app notify entity, if any."""
    entry = er.async_get(hass).async_get(entity_id)
    if entry is None:
        return None
    if entry.platform != "mobile_app":
        return None
    if not entry.device_id:
        return None
    return entry.device_id


def _get_device_name(hass: HomeAssistant, device_id: str) -> str | None:
    """Return the name of a device registry entry, if any."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    return device.name


def _resolve_notify_service_name(hass: HomeAssistant, device_name: str) -> str | None:
    """Return the legacy notify service name for a device, if registered."""
    service_name = slugify(f"mobile_app_{device_name}")
    if not hass.services.has_service("notify", service_name):
        return None
    return service_name


def resolve_legacy_mobile_app_service(
    hass: HomeAssistant,
    entity_id: str,
) -> tuple[str, str] | None:
    """Resolve a mobile_app notify entity to a legacy notify service."""
    device_id = _get_device_id(hass, entity_id)
    if device_id is None:
        return None

    device_name = _get_device_name(hass, device_id)
    if device_name is None:
        return None

    service_name = _resolve_notify_service_name(hass, device_name)
    if service_name is None:
        return None

    return ("notify", service_name)
