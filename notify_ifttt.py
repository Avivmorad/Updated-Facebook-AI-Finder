#!/usr/bin/env python3
"""Send Codex completion notifications to IFTTT.

This script is intentionally resilient:
- It tries to parse a JSON payload from stdin (if present).
- It also supports a JSON payload passed as the last CLI argument.
- It never crashes if webhook delivery fails.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any


WEBHOOK_URL = "https://maker.ifttt.com/trigger/task_done/with/key/cynC4NjZiOGX8NRU7vxPIS"
FALLBACK_MESSAGE = "Codex finished a turn"


def _load_event_payload() -> dict[str, Any]:
    stdin_text = ""
    try:
        if not sys.stdin.isatty():
            stdin_text = sys.stdin.read().strip()
    except Exception:
        stdin_text = ""

    if stdin_text:
        try:
            value = json.loads(stdin_text)
            if isinstance(value, dict):
                return value
        except Exception:
            pass

    if len(sys.argv) > 1:
        arg = (sys.argv[-1] or "").strip()
        if arg.startswith("{") and arg.endswith("}"):
            try:
                value = json.loads(arg)
                if isinstance(value, dict):
                    return value
            except Exception:
                pass

    return {}


def _event_type(payload: dict[str, Any]) -> str:
    for key in ("event", "event_type", "type", "hook_event_name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _build_message(payload: dict[str, Any]) -> str:
    event_type = _event_type(payload)
    if event_type:
        return f"Codex finished: {event_type}"
    return FALLBACK_MESSAGE


def _send_ifttt(message: str) -> None:
    body = json.dumps({"value1": message}).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8):
            pass
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        # Never crash on webhook delivery problems.
        return


def main() -> int:
    payload = _load_event_payload()
    message = _build_message(payload)
    _send_ifttt(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
