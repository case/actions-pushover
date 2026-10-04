# actions-pushover

A reusable GitHub Action to send notifications via the [Pushover](https://pushover.net/) API.

- No external dependencies
- Just `curl` (7.76 or later) and a `POST` to the [Pushover API](https://pushover.net/api)

## Usage

```yaml
- uses: case/actions-pushover@v1
  with:
    pushover_api_token: ${{ secrets.PUSHOVER_API_TOKEN }}
    pushover_user_key: ${{ secrets.PUSHOVER_USER_KEY }}
    title: "{Title here}"
    message: "{Add your message here}"
```

## Inputs

| Input                | Description          | Required |
| -------------------- | -------------------- | -------- |
| `pushover_api_token` | Pushover API token   | Yes      |
| `pushover_user_key`  | Pushover user key    | Yes      |
| `title`              | Notification title   | Yes      |
| `message`            | Notification message | Yes      |

Inputs reach `send.sh` as environment variables and are URL-encoded by `curl`, so quotes, `$()` and `&` in a title or message are sent as text. An empty input fails the step.

The step also fails when Pushover rejects the request (any 4xx or 5xx), and prints Pushover's error list. It gives up after 30 seconds.

## Development

Tools come from `mise.toml`. `bin/setup` installs them, `bin/lint` runs every check, and `bin/ci` runs setup, lint and test in order. `mise.toml` pins Python 3.14, the minimum the tests support. The tests also need `curl`.

`bin/test` runs the stdlib `unittest` suite in `test/`. It checks that `action.yml` never expands an input inside `run:`. It runs `send.sh` against a stub `curl` with hostile inputs, and against a local fake Pushover that answers 200, 400, 429 and 500.

CI runs `bin/ci`, then runs the action itself (`uses: ./`) with hostile inputs and the stub `curl`, which covers the `action.yml` wiring that `bin/test` cannot reach.
