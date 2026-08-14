# Unify Closest Strategies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge `closest` and `closest_with_tolerance` into a single `closest` strategy with optional `tolerance` (default 500 m; `0` = min-distance only, ties included).

**Architecture:** One strategy implementation computes distances to home, finds the minimum, and returns everyone with `distance <= min + tolerance`. Remove the second strategy module and all references. Coordinator/config defaults already supply `tolerance` when the service omits it.

**Tech Stack:** Home Assistant custom integration (`custom_components/smart_notify`), pytest, uv, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-08-08-unify-closest-strategies-design.md`

## Global Constraints

- Python `>=3.13.2`; Home Assistant `>=2026.1.0`
- Ruff line-length `88`
- No alias/deprecation of `closest_with_tolerance` — hard remove
- No config-entry migration
- This workspace may have no git repo — skip commit steps if `.git` is missing (do not `git init` unless the user asks)
- Verify with: `uv run pytest`, `uv run ruff check custom_components tests`, `uv run ty check custom_components tests`

## File map

| File | Action |
|------|--------|
| `custom_components/smart_notify/strategies/closest.py` | Rewrite band + ties logic |
| `custom_components/smart_notify/strategies/closest_with_tolerance.py` | Delete |
| `custom_components/smart_notify/strategies/__init__.py` | Drop import / `__all__` entry |
| `custom_components/smart_notify/const.py` | Remove `STRATEGY_CLOSEST_WITH_TOLERANCE` from choices |
| `custom_components/smart_notify/services.yaml` | Drop option + fix example |
| `tests/test_strategies.py` | Rewrite closest tests; drop old import |
| `tests/conftest.py` | `default_strategy: closest` |
| `tests/test_config_flow.py` | Use `closest` |
| `README.md` | Example uses `closest` |

---

### Task 1: Failing tests for unified `closest`

**Files:**
- Modify: `tests/test_strategies.py`
- Test: `tests/test_strategies.py`

**Interfaces:**
- Consumes: `ClosestStrategy.select_recipients(context: StrategyContext) -> list[str]`
- Produces: Tests that lock band / strict / tie / registry behavior before implementation

- [ ] **Step 1: Rewrite closest-related tests**

Replace the registry assertion, `test_closest_strategy`, and `test_closest_with_tolerance` (and remove the `ClosestWithToleranceStrategy` import) with:

```python
from custom_components.smart_notify.strategies.closest import ClosestStrategy
# remove closest_with_tolerance import


def test_strategy_registry_contains_all_strategies() -> None:
    """Ensure all strategies are registered."""
    names = registry.names()
    assert "everyone" in names
    assert "everyone_home" in names
    assert "everyone_away" in names
    assert "closest" in names
    assert "closest_with_tolerance" not in names
    assert "first_home" in names
    assert "template" in names


def test_closest_tolerance_zero_selects_min_distance_only(hass: MagicMock) -> None:
    """tolerance 0 returns only person(s) at the minimum distance."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={"tolerance": 0})
    recipients = ClosestStrategy().select_recipients(context)
    assert recipients == ["person.alice"]


def test_closest_with_tolerance_band(hass: MagicMock) -> None:
    """Select everyone within tolerance of the closest distance."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.8604, 2.3522),
        make_person("person.charlie", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={"tolerance": 500})
    recipients = ClosestStrategy().select_recipients(context)
    assert "person.alice" in recipients
    assert "person.bob" in recipients
    assert "person.charlie" not in recipients


def test_closest_tolerance_zero_includes_ties(hass: MagicMock) -> None:
    """People at the same minimum distance are all selected."""
    persons = [
        make_person("person.alice", "not_home", 48.8600, 2.3522),
        make_person("person.bob", "not_home", 48.8600, 2.3522),
        make_person("person.charlie", "not_home", 48.9000, 2.3522),
    ]
    context = StrategyContext(hass=hass, persons=persons, params={"tolerance": 0})
    recipients = ClosestStrategy().select_recipients(context)
    assert set(recipients) == {"person.alice", "person.bob"}
```

Leave `test_everyone_home`, `test_first_home_when_away`, and `test_everyone_away_includes_zone_states` unchanged.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_strategies.py -v`

Expected: FAIL — registry still lists `closest_with_tolerance`; band/tie tests fail or import `ClosestWithToleranceStrategy` errors after import removal; `tolerance: 0` may still return a single arbitrary closest if old logic remains (or ImportError if import already removed — remove import in Step 1).

- [ ] **Step 3: Commit (skip if no git)**

```bash
git add tests/test_strategies.py
git commit -m "$(cat <<'EOF'
test: lock unified closest strategy behavior

EOF
)"
```

---

### Task 2: Implement unified `closest` strategy

**Files:**
- Modify: `custom_components/smart_notify/strategies/closest.py`
- Delete: `custom_components/smart_notify/strategies/closest_with_tolerance.py`
- Modify: `custom_components/smart_notify/strategies/__init__.py`

**Interfaces:**
- Consumes: `StrategyContext.params["tolerance"]` (`int`, meters); `distance_to_home_meters`
- Produces: `ClosestStrategy.select_recipients(...) -> list[str]` with band semantics; no `closest_with_tolerance` registration

- [ ] **Step 1: Rewrite `closest.py`**

Replace file contents with:

```python
"""Closest person strategy."""

from __future__ import annotations

import logging

from ..const import DEFAULT_TOLERANCE, LOGGER_NAME, STRATEGY_CLOSEST
from ..util import distance_to_home_meters
from .base import Strategy, StrategyContext, register_strategy

_LOGGER = logging.getLogger(LOGGER_NAME)


@register_strategy
class ClosestStrategy(Strategy):
    """Notify everyone within tolerance of the closest distance to home."""

    name = STRATEGY_CLOSEST

    def select_recipients(self, context: StrategyContext) -> list[str]:
        """Return persons within tolerance of the closest distance."""
        raw = context.params.get("tolerance", DEFAULT_TOLERANCE)
        tolerance = int(DEFAULT_TOLERANCE if raw is None else raw)
        distances: list[tuple[str, float]] = []
        for state in context.persons:
            distance = distance_to_home_meters(context.hass, state)
            if distance is None:
                continue
            distances.append((state.entity_id, distance))
            _LOGGER.debug("Distance for %s: %.1f m", state.entity_id, distance)

        if not distances:
            return []

        minimum = min(distance for _, distance in distances)
        threshold = minimum + tolerance
        recipients = [
            entity_id for entity_id, distance in distances if distance <= threshold
        ]
        _LOGGER.debug(
            "Closest distance %.1f m, tolerance %d m, recipients: %s",
            minimum,
            tolerance,
            recipients,
        )
        return recipients
```

- [ ] **Step 2: Remove old strategy module and registration**

Delete `custom_components/smart_notify/strategies/closest_with_tolerance.py`.

Update `custom_components/smart_notify/strategies/__init__.py` to:

```python
"""Strategy package registration."""

from __future__ import annotations

from . import (
    closest,
    everyone,
    everyone_away,
    everyone_home,
    first_home,
    template,
)
from .base import Strategy, StrategyContext, register_strategy, registry

__all__ = [
    "Strategy",
    "StrategyContext",
    "closest",
    "everyone",
    "everyone_away",
    "everyone_home",
    "first_home",
    "register_strategy",
    "registry",
    "template",
]
```

- [ ] **Step 3: Run strategy tests**

Run: `uv run pytest tests/test_strategies.py -v`

Expected: PASS (all strategy tests)

- [ ] **Step 4: Commit (skip if no git)**

```bash
git add custom_components/smart_notify/strategies/
git commit -m "$(cat <<'EOF'
feat: unify closest strategy with optional tolerance

EOF
)"
```

---

### Task 3: Remove public references to `closest_with_tolerance`

**Files:**
- Modify: `custom_components/smart_notify/const.py`
- Modify: `custom_components/smart_notify/services.yaml`
- Modify: `tests/conftest.py`
- Modify: `tests/test_config_flow.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `STRATEGY_CHOICES` / service selector options
- Produces: Only `closest` as the distance strategy name in UI, schema, fixtures, docs

- [ ] **Step 1: Update `const.py`**

Remove `STRATEGY_CLOSEST_WITH_TOLERANCE` and its entry in `STRATEGY_CHOICES`:

```python
STRATEGY_CLOSEST: Final = "closest"
STRATEGY_FIRST_HOME: Final = "first_home"
STRATEGY_TEMPLATE: Final = "template"

STRATEGY_CHOICES: Final = [
    STRATEGY_EVERYONE,
    STRATEGY_EVERYONE_HOME,
    STRATEGY_EVERYONE_AWAY,
    STRATEGY_CLOSEST,
    STRATEGY_FIRST_HOME,
    STRATEGY_TEMPLATE,
]
```

(Keep surrounding constants unchanged; only delete the with-tolerance constant and list entry.)

- [ ] **Step 2: Update `services.yaml`**

Set strategy example to `closest` and remove `closest_with_tolerance` from options:

```yaml
    strategy:
      required: false
      example: closest
      selector:
        select:
          options:
            - everyone
            - everyone_home
            - everyone_away
            - closest
            - first_home
            - template
```

- [ ] **Step 3: Update fixtures and docs**

In `tests/conftest.py`, change:

```python
"default_strategy": "closest",
```

In `tests/test_config_flow.py`, change:

```python
CONF_DEFAULT_STRATEGY: "closest",
```

In `README.md`, change the usage example to:

```yaml
service: smart_notify.send
data:
  title: Laundry
  message: Washing machine finished.
  strategy: closest
  tolerance: 500
  expire_after: "4h"
```

- [ ] **Step 4: Full verification**

Run:

```bash
uv run ruff check custom_components tests
uv run ruff format --check custom_components tests
uv run ty check custom_components tests
uv run pytest -q
```

Expected: all green; no remaining references to `closest_with_tolerance` under `custom_components/` or `tests/` (spec/plan docs may still mention it historically).

Confirm with:

```bash
rg -n 'closest_with_tolerance|STRATEGY_CLOSEST_WITH_TOLERANCE|ClosestWithTolerance' custom_components tests README.md
```

Expected: no matches.

- [ ] **Step 5: Commit (skip if no git)**

```bash
git add custom_components/smart_notify/const.py \
  custom_components/smart_notify/services.yaml \
  tests/conftest.py tests/test_config_flow.py README.md
git commit -m "$(cat <<'EOF'
chore: drop closest_with_tolerance from API surface

EOF
)"
```

---

## Spec coverage check

| Spec requirement | Task |
|---|---|
| Band selection `min + tolerance` | Task 2 |
| Default tolerance 500 via config/params | Task 2 (`DEFAULT_TOLERANCE`); coordinator already injects |
| `tolerance: 0` = min distance only | Task 1 + 2 |
| Ties at min distance all selected | Task 1 + 2 |
| Delete `closest_with_tolerance` module | Task 2 |
| Remove from const / choices | Task 3 |
| Fixtures / config-flow / README | Task 3 |
| Registry absence assertion | Task 1 |
| No alias / no migration | Honored (hard delete) |
