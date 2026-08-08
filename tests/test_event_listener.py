"""Unit tests for EventListener."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import Event, State

from custom_components.smart_notify.listeners import EventListener

if TYPE_CHECKING:
    from homeassistant.helpers.event import EventStateChangedData


def _state_change_event(
    entity_id: str, old: str, new: str
) -> Event[EventStateChangedData]:
    return cast(
        "Event[EventStateChangedData]",
        Event(
            "state_changed",
            {
                "entity_id": entity_id,
                "old_state": State(entity_id, old),
                "new_state": State(entity_id, new),
            },
        ),
    )


@pytest.mark.asyncio
async def test_arrival_from_zone_invokes_callback(mock_hass: MagicMock) -> None:
    """Named-zone to home transitions count as arrivals."""
    listener = EventListener(mock_hass, ["person.alice"])
    callback = AsyncMock()
    listener.set_arrival_callback(callback)

    await listener._async_handle_person_change(
        _state_change_event("person.alice", "Work", "home")
    )

    callback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_persons_resubscribes(mock_hass: MagicMock) -> None:
    """Updating tracked persons restarts the state listener."""
    listener = EventListener(mock_hass, ["person.alice"])
    first_unsub = MagicMock()
    second_unsub = MagicMock()

    with patch(
        "custom_components.smart_notify.listeners.async_track_state_change_event",
        side_effect=[first_unsub, second_unsub],
    ) as track:
        await listener.async_start()
        await listener.async_update_persons(["person.alice", "person.bob"])

    first_unsub.assert_called_once()
    assert track.call_count == 2
    assert track.call_args_list[1].args[1] == ["person.alice", "person.bob"]
    assert listener._unsubscribes == [second_unsub]
