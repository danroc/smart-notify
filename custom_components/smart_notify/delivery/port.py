"""Port for delivering a built notify payload to a single target."""

from __future__ import annotations

from typing import Any, Protocol


class NotifyPort(Protocol):
    """Delivers notify service data to one configured notify target."""

    async def send(self, target: str, data: dict[str, Any]) -> None:
        """Deliver ``data`` to ``target``.

        ``target`` is a configured notify target as it appears in
        ``SmartNotifyConfig.person_services`` -- either a legacy
        ``domain.service`` pair (e.g. ``notify.mobile_app_alice``) or a
        notify entity id (e.g. ``notify.daniel_iphone``). Implementations
        own all target-resolution details.

        Raises:
            Exception: the target does not exist or delivery failed.
                Callers treat any exception as "this target failed".

        """
        ...
