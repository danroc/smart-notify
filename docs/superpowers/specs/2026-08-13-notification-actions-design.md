# Design: Notification actions (send-only)

Date: 2026-08-13
Status: Implemented
Scope: Top-level `actions` on `smart_notify.send`; reliable delivery to Companion app targets (including notify entities). No action handling in Smart Notify.

## Goal

Callers can attach actionable notification buttons (long-press on iOS, expanded actions on Android) when using `smart_notify.send`. Smart Notify delivers `actions` to the phone; automations elsewhere listen for `mobile_app_notification_action` as usual.

## Locked decisions

- **Send-only.** Smart Notify does not listen for or handle action callbacks. No `smart_notify_action` event, no built-in service runners.
- **Top-level `actions` field** on `smart_notify.send`.
- **Fix notify-entity delivery.** When a configured target is a notify entity and the payload includes rich mobile fields (`actions`, `level`, `url`, `group`, `image`, `tag`), resolve to the matching legacy `notify.mobile_app_*` service. HA's `notify.send_message` does not accept a nested `data` block, so passing `data` into that path cannot deliver those fields.
- **Config flow unchanged.** Per-person targets remain notify entities or legacy services selected in the UI.
- Mobile-app options (`level`, `tag`, `group`, `image`, `url`, `actions`) are top-level service fields. There is no generic `data` bag on `smart_notify.send`.

## API

```yaml
service: smart_notify.send
data:
  title: Laundry
  message: Washing machine finished.
  strategy: arrival
  persons:
    - person.daniel
  tag: laundry
  actions:
    - action: LAUNDRY_ACK
      title: Got it
    - action: LAUNDRY_SNOOZE
      title: Remind in 1 hour
```

With a URL action button:

```yaml
service: smart_notify.send
data:
  message: Motion detected in the backyard.
  strategy: home
  actions:
    - action: URI
      title: View cameras
      uri: /lovelace/security
```

### Field rules

| Field | Required | Notes |
|---|---|---|
| `actions` | No | List of action objects. Omitted → plain notification (no buttons). |
| `action` (per item) | Yes | Identifier returned in `mobile_app_notification_action`. |
| `title` (per item) | Yes | Button label shown on the device. |
| `uri` (per item) | No | Required when `action` is `URI`. Lovelace path or URL. |

Schema: optional list; when present, each item is a dict with required string keys `action` and `title`. Additional keys (e.g. `uri`) pass through unchanged. No max action count enforced by Smart Notify (Companion app limits apply).

### Invalid patterns

Do **not** nest mobile fields under a service `data` bag — those keys are rejected by the schema.

### Notify payload assembly

At delivery time, `_build_notify_data` constructs the notify service call:

1. `message`, `title` from the payload (unchanged).
2. Build notify `data` dict from top-level payload fields:
   - `group`, `image`, `url`, `tag`, `actions`
   - `level` → per-level notify data: `push.interruption-level` for iOS plus
     `priority` and `ttl` for Android. `normal` contributes nothing.
3. Omit notify `data` entirely when it would be empty.

Example notify call for the laundry example above:

```yaml
message: Washing machine finished.
title: Laundry
data:
  tag: laundry
  actions:
    - action: LAUNDRY_ACK
      title: Got it
    - action: LAUNDRY_SNOOZE
      title: Remind in 1 hour
```

### Action handling (out of Smart Notify)

Automations listen for the standard Companion app event:

```yaml
automation:
  alias: Laundry notification actions
  triggers:
    - trigger: event
      event_type: mobile_app_notification_action
      event_data:
        action: LAUNDRY_ACK
  actions:
    - action: input_boolean.turn_off
      target:
        entity_id: input_boolean.laundry_reminder
```

See [Companion actionable notifications](https://companion.home-assistant.io/docs/notifications/actionable-notifications/).

## Storage and queue

- Add `actions: list[dict[str, Any]] | None` to `NotificationPayload`.
- Serialize/deserialize in `to_dict` / `from_dict` so queued notifications retain actions until flush.
- Queue flush reuses stored `actions` with the same delivery logic as immediate sends.

## Delivery

### Legacy service path (`notify.mobile_app_*`)

No change. `_build_notify_data` already produces the correct shape; legacy services accept `data.actions`.

### Notify entity path

HA's `notify.send_message` accepts only `message` and `title`. The Companion app notify entity cannot receive `data.actions` through that service.

| Payload | Behavior |
|---|---|
| Plain title/message only | `notify.send_message` with `message` + `title` (current behavior). |
| Any rich mobile field (`actions`, `level` other than `normal`, `url`, `group`, `image`, `tag`) | Attempt entity → legacy resolution (below). |

**Entity → legacy resolution** (mobile_app only):

1. Read entity registry entry for the target `notify.*` entity.
2. If `platform == "mobile_app"` and `device_id` is set, load the device from the device registry.
3. Build candidate service name: `notify.{slugify(f"mobile_app_{device.name}")}` (matches HA's legacy registration).
4. If `hass.services.has_service("notify", service_name)`, deliver via the legacy service with the full notify payload from `_build_notify_data`.
5. Otherwise log a warning and fall back to plain `notify.send_message` (title + message only; actions dropped).

Remove the current "Ignoring notify data for entity" warning when resolution succeeds. Log a clear warning only when rich payload is dropped on fallback.

Non-`mobile_app` notify entities with `actions`: same fallback behavior (warning + plain message). Extending other platforms is out of scope.

## Code changes

1. Add `ATTR_ACTIONS` to `const.py`.
2. Add optional `actions` to `SERVICE_SEND_SCHEMA`, `services.yaml`, and `NotificationPayload`.
3. Coordinator `_build_payload`: read flat mobile fields from top-level service data.
4. `DeliveryManager._build_notify_data`: assemble notify `data` from flat payload fields.
5. `DeliveryManager._async_call_notify`: implement entity → legacy fallback when notify `data` is non-empty; remove unconditional data-stripping on entity path.
6. README: actionable notification example and link to `mobile_app_notification_action`.
7. Tests for schema, payload build, legacy pass-through, entity resolution, fallback, and queued flush.

## Testing

- `actions` omitted → notify call has no `data.actions` (plain notification).
- Top-level `actions` → notify `data.actions` present; not nested under `data.data`.
- `tag`, `url`, `group`, `image`, `level` → merged into notify `data` as appropriate.
- Legacy `notify.mobile_app_*` target → full payload delivered (existing path).
- Notify entity, no actions → `send_message` only (unchanged).
- Notify entity + `actions`, resolvable `mobile_app` entity → legacy service called with `data.actions`.
- Notify entity + `actions`, unresolvable entity → warning + plain `send_message`.
- Queued notification with `actions` → same behavior on flush.

## Out of scope

- `smart_notify_action` events or built-in action handlers.
- iOS action categories, `REPLY` / text-input actions, action icons.
- Non-`mobile_app` notify entities with rich payloads.
- Telegram or other notify platforms.
