# Design: Person filter and remove template strategy

Date: 2026-08-13
Status: Approved for planning
Scope: Optional `persons` filter on `smart_notify.send`; delete the `template` strategy. No Telegram, no named channels, no presence-radius.

## Goal

Callers can target one (or more) configured people on a send. Strategies still decide *whether* those people receive the notification. The unused Jinja `template` strategy goes away.

## Locked decisions

- Presence is HA `home` / not `home`. Do not add a nearby radius.
- `tolerance` stays only on `closest` (band around the closest person, not around home).
- Arrival / queue stays as today: persist when nobody matches, flush when someone enters `home`.
- Per-person notify services stay a list of `notify.*` targets (companion app). No Telegram chat/thread config.
- No `channels` field on send.

## Behavior

### Person filter

Optional service field `persons`: a list of `person.*` entity IDs.

| Call input | Candidates passed to the strategy |
|---|---|
| `persons` omitted | All configured persons (today's behavior) |
| `persons: [person.daniel]` | Intersection of that list with configured persons |
| `persons: [person.daniel, person.luiza]` | Intersection of that list with configured persons |

Unknown or unconfigured entity IDs are dropped. If every ID is unknown, the candidate set is empty, the strategy returns `[]`, and strategy-specific queue behavior applies (`arrival` and `closest` queue; others drop).

If `persons` is present, it must contain at least one string (empty list is invalid).

The filter runs **before** the strategy. Eligibility (`unavailable` / `unknown` skipped) still applies to the filtered set.

Examples:

- `strategy: everyone` + `persons: [person.daniel]` → notify Daniel now (if eligible).
- `strategy: everyone_home` + `persons: [person.daniel]` → notify Daniel only if he is `home`; otherwise queue (default) or drop.
- `strategy: closest` + `persons: [person.daniel]` → closest among Daniel only (so Daniel if he has a usable distance).

### Queue

Store the filter on the notification payload (`persons: list[str] | None`). Queue flush must reuse that list so a targeted send does not later fan out to every configured person when someone arrives.

`None` / omitted on a stored payload means all configured persons (backward compatible with existing queue entries).

### Template removal

Remove strategy name `template`, file `strategies/template.py`, service field `template`, and payload field `template`.

This is a breaking API change: `strategy: template` becomes invalid. No alias. No migration of queued items that used `template`; if one exists, flush treats it as an unknown strategy and marks that item failed.

Config flow / options strategy dropdown lose `template` automatically via `STRATEGY_CHOICES`.

## API

```yaml
service: smart_notify.send
data:
  message: Washing machine finished.
  strategy: everyone
  persons:
    - person.daniel
```

- Selector: person entities, multiple.
- Schema: optional list of entity IDs, min length 1 when present.
- Config entry data shape unchanged (`persons` in config remains the household roster; service `persons` is a per-call subset).

## Code changes

1. Delete `custom_components/smart_notify/strategies/template.py` and drop it from the strategies package.
2. Remove `STRATEGY_TEMPLATE` from `const.py` / `STRATEGY_CHOICES`.
3. Add `ATTR_PERSONS` and optional `persons` on the send schema, `services.yaml`, and `NotificationPayload`.
4. `RecipientResolver` accepts an optional candidate list and intersects with configured eligible persons before calling the strategy.
5. Coordinator `async_send` and queue flush pass the payload's `persons` into resolve.
6. Drop `template` from payload build, strategy params, service schema, and README if mentioned.
7. Tests and config-flow strategy options follow `STRATEGY_CHOICES`.

## Testing

- Omit `persons` → same recipients as today.
- `persons: [person.alice]` with two configured people and `everyone` → only Alice.
- Unconfigured ID dropped; only configured IDs remain.
- All IDs unconfigured + `strategy: arrival` → queued.
- `everyone_home` + Alice away + filter Alice → no immediate delivery (queue).
- Queued notification with `persons: [person.alice]` still targets only Alice after flush.
- Empty `persons: []` rejected by schema.
- Registry / service selector: `template` absent; other strategies unchanged.
- `strategy: template` rejected by schema.

## Out of scope

- Telegram / `telegram_bot.send_message`.
- Presence radius or changing `closest` / `first_home` / `everyone_home`.
