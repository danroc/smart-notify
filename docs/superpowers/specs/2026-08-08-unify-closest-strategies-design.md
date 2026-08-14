# Design: Unify closest strategies

Date: 2026-08-08  
Status: Approved for planning  
Scope: Merge `closest` and `closest_with_tolerance` into a single `closest` strategy

## Goal

One recipient strategy, `closest`, with an optional `tolerance` parameter (meters). Remove `closest_with_tolerance` as a separate strategy name.

## Behavior

Select every eligible person whose distance to home is `≤ min_distance + tolerance`.

| Call input | Effective tolerance | Result |
|---|---|---|
| `tolerance` omitted | Config `default_tolerance` (500) | Everyone within 500 m of the closest distance |
| `tolerance: 0` | 0 | Everyone at the minimum distance |
| `tolerance: N` | N | Everyone within N m of the closest distance |

### Ties

If two or more people share the minimum distance, all of them are selected when `tolerance` is `0` (and likewise when they fall inside a larger band).

### Ineligible / empty

People without latitude/longitude are skipped (unchanged). If nobody has a usable distance, return `[]` (`arrival` and `closest` queue when empty; other strategies drop).

## API / config

- Strategy choices expose only `closest` (drop `closest_with_tolerance`).
- Service field `tolerance` and config `default_tolerance` stay as today; coordinator already injects the config default into strategy params when the service omits `tolerance`.
- Default strategy in fixtures / examples becomes `closest` where it currently says `closest_with_tolerance`.
- No config-entry migration: treat as breaking rename; callers must use `strategy: closest`.

## Code changes

1. Rewrite `strategies/closest.py` to implement band selection (`min + tolerance`).
2. Delete `strategies/closest_with_tolerance.py` and remove its package import.
3. Remove `STRATEGY_CLOSEST_WITH_TOLERANCE` from `const.py` / `STRATEGY_CHOICES`.
4. Update tests, conftest, config-flow tests, and README examples.

## Testing

- Band case: several people, `tolerance: 500` → near ones included, far ones not.
- Strict case: `tolerance: 0` → only min-distance person(s).
- Tie case: two people at the same distance, `tolerance: 0` → both selected.
- Registry: `closest` present; `closest_with_tolerance` absent.
- Fixtures / config-flow tests use `closest`.

## Out of scope

- Changing how distance is computed.
- Aliasing or deprecating `closest_with_tolerance`.
