from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.browser import BrowserConfig
from app.utils.debugging import debug_info, debug_warning


_SAFE_CODE_RE = re.compile(r"[^a-zA-Z0-9_]+")


def is_step_debug_enabled(config: BrowserConfig) -> bool:
    return bool(config.step_debug_enabled)


def reset_step_debug_workspace(config: BrowserConfig) -> Optional[Path]:
    if not is_step_debug_enabled(config):
        return None

    workspace = _workspace_dir(config)
    workspace.mkdir(parents=True, exist_ok=True)

    for item in workspace.glob("*.png"):
        item.unlink(missing_ok=True)
    events_path = workspace / "events.jsonl"
    events_path.write_text("", encoding="utf-8")
    debug_info("DBG_BROWSER_STEP_WORKSPACE", f"Prepared browser step workspace: {workspace}")
    return workspace


def capture_browser_step(
    config: BrowserConfig,
    *,
    page: Any,
    step_code: str,
    message: str,
    context: str = "",
) -> str:
    if not is_step_debug_enabled(config):
        return ""
    if page is None:
        return ""

    workspace = _workspace_dir(config)
    workspace.mkdir(parents=True, exist_ok=True)

    safe_code = _SAFE_CODE_RE.sub("_", str(step_code or "step")).strip("_") or "step"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    image_path = workspace / f"{stamp}_{safe_code}.png"

    try:
        page.screenshot(path=str(image_path), full_page=True)
    except Exception as exc:  # noqa: BLE001
        debug_warning("DBG_BROWSER_STEP_CAPTURE_FAIL", f"Failed capturing browser step screenshot: {exc}")
        return ""

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step_code": str(step_code or "").strip(),
        "message": str(message or "").strip(),
        "context": str(context or "").strip(),
        "image_name": image_path.name,
        "image_path": str(image_path),
        "url": str(getattr(page, "url", "") or "").strip(),
    }
    _append_event(workspace / "events.jsonl", event)
    debug_info("DBG_BROWSER_STEP_CAPTURED", f"Captured browser step: {event['step_code']} -> {image_path.name}")
    return str(image_path)


def load_step_events(config: BrowserConfig, *, limit: int = 60) -> Dict[str, Any]:
    workspace = _workspace_dir(config)
    events_path = workspace / "events.jsonl"
    if not workspace.exists() or not events_path.exists():
        return {
            "enabled": is_step_debug_enabled(config),
            "workspace": str(workspace),
            "events": [],
        }

    events: List[Dict[str, str]] = []
    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []

    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        events.append(
            {
                "timestamp": str(payload.get("timestamp", "")),
                "step_code": str(payload.get("step_code", "")),
                "message": str(payload.get("message", "")),
                "context": str(payload.get("context", "")),
                "image_name": str(payload.get("image_name", "")),
                "url": str(payload.get("url", "")),
            }
        )

    if limit > 0 and len(events) > limit:
        events = events[-limit:]

    return {
        "enabled": is_step_debug_enabled(config),
        "workspace": str(workspace),
        "events": events,
    }


def _workspace_dir(config: BrowserConfig) -> Path:
    return Path(config.step_debug_dir).expanduser()


def _append_event(path: Path, payload: Dict[str, str]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded + "\n")

