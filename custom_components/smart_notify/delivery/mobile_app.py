"""Resolve mobile app notify entities to legacy notify services."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify


def resolve_legacy_mobile_app_service(
    hass: HomeAssistant,
    entity_id: str,
) -> tuple[str, str] | None:
    """Resolve a mobile_app notify entity to a legacy notify service."""
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None or entry.platform != "mobile_app" or not entry.device_id:
        return None

    device_registry = dr.async_get(hass)
    device = device_registry.async_get(entry.device_id)
    if device is None:
        return None

    service_name = slugify(f"mobile_app_{device.name}")
    if not hass.services.has_service("notify", service_name):
        return None
    return ("notify", service_name)
