"""Reads the argv the stub curl recorded and checks what it sent to Pushover."""

import json
from itertools import pairwise

API_URL = "https://api.pushover.net/1/messages.json"


def load_args(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def problems(args: list[str], expected: dict[str, str]) -> list[str]:
    """Returns one message per expected field not sent verbatim, empty when the call is right."""
    found = []
    # Plain --data would pass "& title=evil" through as a second title parameter.
    pairs = set(pairwise(args))
    for name, value in expected.items():
        if ("--data-urlencode", f"{name}={value}") not in pairs:
            found.append(f"curl did not receive {name} verbatim via --data-urlencode")
    if not args or args[-1] != API_URL:
        found.append("curl did not receive the API URL")
    return found
