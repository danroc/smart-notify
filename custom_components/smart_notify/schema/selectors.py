"""Home Assistant UI selectors for Smart Notify."""

from __future__ import annotations

from collections.abc import Mapping

from homeassistant.helpers import selector

from ..const import LEVEL_LABELS, LOG_LEVELS, STRATEGY_LABELS


def _labeled_options(
    labels: Mapping[str, str],
) -> list[selector.SelectOptionDict]:
    """Return select options from a value-to-label mapping."""
    return [{"value": value, "label": label} for value, label in labels.items()]


def strategy_selector() -> selector.Selector[selector.SelectSelectorConfig]:
    """Return the strategy dropdown selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=_labeled_options(STRATEGY_LABELS)),
    )


def level_selector() -> selector.Selector[selector.SelectSelectorConfig]:
    """Return the notification level dropdown selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=_labeled_options(LEVEL_LABELS)),
    )


def log_level_selector() -> selector.Selector[selector.SelectSelectorConfig]:
    """Return the integration log-level dropdown selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=list(LOG_LEVELS)),
    )


def tolerance_selector() -> selector.Selector[selector.NumberSelectorConfig]:
    """Return the closest-strategy tolerance selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            step=50,
            mode=selector.NumberSelectorMode.BOX,
        ),
    )


def duration_selector() -> selector.Selector[selector.TextSelectorConfig]:
    """Return the expire-after duration text selector."""
    return selector.TextSelector()


def person_selector() -> selector.Selector[selector.EntitySelectorConfig]:
    """Return a multi-person entity selector."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="person", multiple=True),
    )


def notify_selector() -> selector.Selector[selector.EntitySelectorConfig]:
    """Return a multi-notify entity selector."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="notify", multiple=True),
    )


def arrival_debounce_selector() -> selector.Selector[selector.NumberSelectorConfig]:
    """Return the arrival debounce selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            max=600,
            step=5,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="seconds",
        ),
    )
