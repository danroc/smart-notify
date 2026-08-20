"""Shared voluptuous schemas, selectors, and services.yaml catalog.

Send field definitions in ``SEND_FIELDS`` drive ``SERVICE_SEND_SCHEMA`` and
``render_services_yaml()``. After changing send fields, update the committed
``services.yaml`` from the catalog (``tests/test_schema.py`` asserts they match):

    uv run python -c "
from pathlib import Path
import yaml
from custom_components.smart_notify.schema import render_services_yaml
path = Path('custom_components/smart_notify/services.yaml')
path.write_text(yaml.safe_dump(render_services_yaml(), sort_keys=False))
"
"""

from __future__ import annotations

from .defaults import defaults_schema_fields
from .selectors import (
    arrival_debounce_selector,
    duration_selector,
    level_selector,
    log_level_selector,
    notify_selector,
    person_selector,
    strategy_selector,
    tolerance_selector,
)
from .send import (
    SEND_FIELDS,
    SERVICE_SEND_DESCRIPTION,
    SERVICE_SEND_NAME,
    SERVICE_SEND_SCHEMA,
    SendField,
    render_services_yaml,
    selector_to_yaml,
)
from .storage_schemas import (
    QUEUE_ITEM_SCHEMA,
    QUEUE_PAYLOAD_SCHEMA,
    QUEUE_STATUS_CHOICES,
    STORAGE_SCHEMA,
)
from .validators import (
    ACTION_SCHEMA,
    CV_ACTIONS,
    CV_LEVEL,
    CV_LOG_LEVEL,
    CV_PERSONS,
    CV_STRATEGY,
    CV_TOLERANCE,
    cv_duration,
)

__all__ = [
    "ACTION_SCHEMA",
    "CV_ACTIONS",
    "CV_LEVEL",
    "CV_LOG_LEVEL",
    "CV_PERSONS",
    "CV_STRATEGY",
    "CV_TOLERANCE",
    "QUEUE_ITEM_SCHEMA",
    "QUEUE_PAYLOAD_SCHEMA",
    "QUEUE_STATUS_CHOICES",
    "SEND_FIELDS",
    "SERVICE_SEND_DESCRIPTION",
    "SERVICE_SEND_NAME",
    "SERVICE_SEND_SCHEMA",
    "STORAGE_SCHEMA",
    "SendField",
    "arrival_debounce_selector",
    "cv_duration",
    "defaults_schema_fields",
    "duration_selector",
    "level_selector",
    "log_level_selector",
    "notify_selector",
    "person_selector",
    "render_services_yaml",
    "selector_to_yaml",
    "strategy_selector",
    "tolerance_selector",
]
