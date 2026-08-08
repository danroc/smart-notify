"""Template strategy."""

from __future__ import annotations

import logging

from homeassistant.helpers.template import Template

from ..const import LOGGER_NAME, STRATEGY_TEMPLATE
from .base import Strategy, StrategyContext, register_strategy

_LOGGER = logging.getLogger(LOGGER_NAME)


@register_strategy
class TemplateStrategy(Strategy):
    """Select recipients using a Jinja template."""

    name = STRATEGY_TEMPLATE

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Evaluate a template returning person entity IDs."""
        template_value = context.params.get("template")
        if not template_value:
            _LOGGER.warning("Template strategy requested without template parameter")
            return []

        template = Template(template_value, context.hass)
        rendered = template.async_render(parse_result=False)
        recipients = _normalize_template_result(rendered)
        configured = {state.entity_id for state in context.persons}
        return [entity_id for entity_id in recipients if entity_id in configured]


def _normalize_template_result(result: object) -> list[str]:
    """Normalize template output to a list of entity IDs."""
    if isinstance(result, str):
        return [result]
    if isinstance(result, list):
        return [str(item) for item in result]
    return []
