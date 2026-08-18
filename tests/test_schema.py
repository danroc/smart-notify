"""Tests for shared schema catalog and derived artifacts."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
import yaml

from custom_components.smart_notify.const import (
    CONF_ARRIVAL_DEBOUNCE_SECONDS,
    CONF_DEFAULT_EXPIRE_AFTER,
    CONF_DEFAULT_STRATEGY,
    CONF_DEFAULT_TOLERANCE,
    CONF_LOG_LEVEL,
    LEVEL_CHOICES,
    LEVEL_LABELS,
    LOG_LEVELS,
    QUEUE_SCHEMA_VERSION,
    STRATEGY_LABELS,
)
from custom_components.smart_notify.schema import (
    QUEUE_PAYLOAD_SCHEMA,
    SERVICE_SEND_SCHEMA,
    cv_duration,
    defaults_schema_fields,
    log_level_selector,
    render_services_yaml,
    strategy_selector,
)
from custom_components.smart_notify.storage import SmartNotifyStorage
from tests.conftest import make_payload

SERVICES_YAML = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "smart_notify"
    / "services.yaml"
)


def test_render_services_yaml_matches_committed_file() -> None:
    """Committed services.yaml is generated from the Python catalog."""
    committed = yaml.safe_load(SERVICES_YAML.read_text(encoding="utf-8"))
    assert committed == render_services_yaml()


def test_cv_duration_accepts_shorthand() -> None:
    """Duration validator keeps valid shorthand strings."""
    assert cv_duration("4h") == "4h"
    assert cv_duration("30m") == "30m"


def test_cv_duration_rejects_invalid() -> None:
    """Duration validator raises vol.Invalid for bad values."""
    with pytest.raises(vol.Invalid):
        cv_duration("bad")


def test_service_schema_rejects_invalid_expire_after() -> None:
    """Send schema rejects durations that parse_duration would reject."""
    with pytest.raises(vol.Invalid):
        SERVICE_SEND_SCHEMA({"message": "Hello", "expire_after": "bad"})


def test_service_schema_accepts_valid_expire_after() -> None:
    """Send schema accepts duration shorthand."""
    validated = SERVICE_SEND_SCHEMA({"message": "Hello", "expire_after": "4h"})
    assert validated["expire_after"] == "4h"


def test_defaults_schema_rejects_invalid_expire_after() -> None:
    """Config defaults reject invalid duration shorthand."""
    schema = vol.Schema(defaults_schema_fields())
    with pytest.raises(vol.Invalid):
        schema({
            CONF_DEFAULT_STRATEGY: "closest",
            CONF_DEFAULT_TOLERANCE: 500,
            CONF_DEFAULT_EXPIRE_AFTER: "bad",
            CONF_ARRIVAL_DEBOUNCE_SECONDS: 30,
            CONF_LOG_LEVEL: "info",
        })


def test_log_level_selector_options_match_const() -> None:
    """Log-level dropdown is derived from LOG_LEVELS."""
    assert log_level_selector().config["options"] == list(LOG_LEVELS)


def test_strategy_selector_options_match_labels() -> None:
    """Strategy dropdown is derived from STRATEGY_LABELS."""
    options = [
        option
        for option in strategy_selector().config["options"]
        if isinstance(option, dict)
    ]
    assert {option["value"]: option["label"] for option in options} == STRATEGY_LABELS


def test_level_labels_cover_choices() -> None:
    """Level UI labels exist for every level choice."""
    assert list(LEVEL_LABELS) == list(LEVEL_CHOICES)
    assert all(label[0].isupper() for label in LEVEL_LABELS.values())


def test_queue_payload_schema_keeps_unknown_strategy() -> None:
    """Stored payloads may carry removed strategy names for flush-as-failed."""
    data = make_payload().to_dict() | {"strategy": "first_home"}
    validated = QUEUE_PAYLOAD_SCHEMA(data)
    assert validated["strategy"] == "first_home"


def test_queue_payload_schema_rejects_invalid_level() -> None:
    """Stored payloads with unknown urgency are invalid."""
    data = make_payload().to_dict() | {"level": "bogus"}
    with pytest.raises(vol.Invalid):
        QUEUE_PAYLOAD_SCHEMA(data)


def test_queue_payload_schema_allows_legacy_template_key() -> None:
    """Unknown historical keys do not fail queue payload validation."""
    data = make_payload().to_dict() | {"template": "{{ states.person | list }}"}
    validated = QUEUE_PAYLOAD_SCHEMA(data)
    assert validated["template"] == "{{ states.person | list }}"


@pytest.mark.asyncio
async def test_storage_load_skips_queue_item_with_invalid_level(
    hass: MagicMock,
) -> None:
    """Corrupt urgency on a queue item is skipped, not coerced."""
    payload = make_payload().to_dict() | {"level": "bogus"}
    storage = SmartNotifyStorage(hass)
    storage._store.async_load = AsyncMock(
        return_value={
            "schema_version": QUEUE_SCHEMA_VERSION,
            "queue": [
                {"id": payload["id"], "status": "pending", "payload": payload},
            ],
        }
    )

    await storage.async_load()

    assert storage.get_queue() == []


@pytest.mark.asyncio
async def test_storage_load_keeps_unknown_strategy(hass: MagicMock) -> None:
    """Unknown stored strategies remain available for flush-as-failed."""
    payload = make_payload().to_dict() | {"strategy": "first_home"}
    storage = SmartNotifyStorage(hass)
    storage._store.async_load = AsyncMock(
        return_value={
            "schema_version": QUEUE_SCHEMA_VERSION,
            "queue": [
                {"id": payload["id"], "status": "pending", "payload": payload},
            ],
        }
    )

    await storage.async_load()

    queue = storage.get_queue()
    assert len(queue) == 1
    assert queue[0].strategy == "first_home"
