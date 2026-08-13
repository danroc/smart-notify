# Smart Notify

Home Assistant custom integration that routes notifications based on presence, distance,
and configurable delivery strategies.

## Installation

Copy `custom_components/smart_notify` into your Home Assistant
`config/custom_components` directory and restart Home Assistant.

## Usage

```yaml
service: smart_notify.send
data:
  title: Laundry
  message: Washing machine finished.
  strategy: arrival
  persons:
    - person.daniel
  expire_after: "4h"
```

`persons` is optional. Omit it to consider every person configured in the integration.

| Strategy  | Who is notified                                           | Empty set                                   |
| --------- | --------------------------------------------------------- | ------------------------------------------- |
| `direct`  | Everyone eligible                                         | Drop (unless `queue_if_no_candidate: true`) |
| `home`    | People at home now                                        | Drop (unless `queue_if_no_candidate: true`) |
| `away`    | People away now                                           | Drop (unless `queue_if_no_candidate: true`) |
| `closest` | People within `tolerance` of the closest distance to home | Queue until someone has a usable location   |
| `arrival` | People at home now                                        | Queue until someone arrives home            |

The queue only retries when someone enters the home zone. `away` does not wait for a
departure.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.2+ (Home Assistant 2026.x).

```bash
# Install dependencies and create .venv
uv sync

# Lint
uv run ruff check custom_components tests

# Type check
uv run ty check custom_components tests

# Test
uv run pytest
```

### Common uv commands

| Command                    | Description                                          |
| -------------------------- | ---------------------------------------------------- |
| `uv sync`                  | Install / update locked dependencies                 |
| `uv lock`                  | Regenerate `uv.lock` after changing `pyproject.toml` |
| `uv add --group dev <pkg>` | Add a dev dependency                                 |
| `uv run <cmd>`             | Run a command in the project virtualenv              |
