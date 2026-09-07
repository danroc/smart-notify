"""Event listeners for Smart Notify."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)

from .const import HOME_STATES, LOGGER_NAME

_LOGGER = logging.getLogger(LOGGER_NAME)

PersonTransitionCallback = Callable[[str, State, State], Awaitable[None]]


def _classify_transition(old_value: str, new_value: str) -> str | None:
    """Return "arrival", "departure", or None for a person state transition."""
    if old_value in {STATE_UNAVAILABLE, STATE_UNKNOWN}:
        return None
    if new_value in {STATE_UNAVAILABLE, STATE_UNKNOWN}:
        return None
    if old_value not in HOME_STATES and new_value in HOME_STATES:
        return "arrival"
    if old_value in HOME_STATES and new_value not in HOME_STATES:
        return "departure"
    return None


class EventListener:
    """Subscribe to Home Assistant events relevant to Smart Notify."""

    def __init__(self, hass: HomeAssistant, person_ids: list[str]) -> None:
        """Initialize listener."""
        self._hass = hass
        self._person_ids = person_ids
        self._unsubscribes: list[Callable[[], None]] = []
        self._arrival_callback: PersonTransitionCallback | None = None
        self._departure_callback: PersonTransitionCallback | None = None

    def set_arrival_callback(self, callback_func: PersonTransitionCallback) -> None:
        """Set callback for person arrival events."""
        self._arrival_callback = callback_func

    def set_departure_callback(self, callback_func: PersonTransitionCallback) -> None:
        """Set callback for person departure events."""
        self._departure_callback = callback_func

    async def async_update_persons(self, person_ids: list[str]) -> None:
        """Update tracked person entities and resubscribe."""
        await self.async_stop()
        self._person_ids = person_ids
        await self.async_start()

    async def async_start(self) -> None:
        """Start listening for person state changes."""
        if not self._person_ids:
            return

        @callback
        def _handle_person_change(event: Event[EventStateChangedData]) -> None:
            self._hass.async_create_task(self._async_handle_person_change(event))

        unsubscribe = async_track_state_change_event(
            self._hass,
            self._person_ids,
            _handle_person_change,
        )
        self._unsubscribes.append(unsubscribe)
        _LOGGER.debug("Listening for person changes: %s", self._person_ids)

    async def _async_handle_person_change(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle a person state change."""
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if old_state is None or new_state is None:
            return

        transition = _classify_transition(old_state.state, new_state.state)
        if transition is None:
            return

        _LOGGER.debug(
            "Person %s detected: %s (%s -> %s)",
            transition,
            new_state.entity_id,
            old_state.state,
            new_state.state,
        )

        callback_func = (
            self._arrival_callback
            if transition == "arrival"
            else self._departure_callback
        )
        if callback_func is not None:
            await callback_func(new_state.entity_id, old_state, new_state)

    async def async_stop(self) -> None:
        """Stop all listeners."""
        for unsubscribe in self._unsubscribes:
            unsubscribe()
        self._unsubscribes.clear()
