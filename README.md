# actions-pushover

A reusable GitHub Action to send notifications via the [Pushover](https://pushover.net/) API.

- No external dependencies
- Just `curl` and a `POST` to the [Pushover API](https://pushover.net/api)

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

| Input | Description | Required |
|-------|-------------|----------|
| `pushover_api_token` | Pushover API token | Yes |
| `pushover_user_key` | Pushover user key | Yes |
| `title` | Notification title | Yes |
| `message` | Notification message | Yes |
