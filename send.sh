#!/usr/bin/env bash
# Sends one Pushover message. Inputs arrive as environment variables, never as script text.
set -euo pipefail

: "${PUSHOVER_API_TOKEN:?pushover_api_token is required}"
: "${PUSHOVER_USER_KEY:?pushover_user_key is required}"
: "${PUSHOVER_TITLE:?title is required}"
: "${PUSHOVER_MESSAGE:?message is required}"

# --data-urlencode name=value encodes the value literally, so quotes, & and @ stay data.
# --fail-with-body fails the step on a 4xx or 5xx and still prints Pushover's error list.
curl -sS --fail-with-body --max-time 30 \
  --data-urlencode "token=$PUSHOVER_API_TOKEN" \
  --data-urlencode "user=$PUSHOVER_USER_KEY" \
  --data-urlencode "title=$PUSHOVER_TITLE" \
  --data-urlencode "message=$PUSHOVER_MESSAGE" \
  https://api.pushover.net/1/messages.json
