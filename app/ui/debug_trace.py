from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


_DEBUG_LINE_RE = re.compile(
    r"^\[DEBUG (?P<clock>\d{2}:\d{2}:\d{2})\] (?P<kind>[A-Z]+) (?P<code>[A-Z0-9_]+) \| (?P<message>.*)$"
)

_STAGE_CODE_MAP = {
    "DBG_RUN_START": "run",
    "DBG_STARTUP_CHECK": "startup",
    "DBG_PIPELINE_START": "pipeline",
    "DBG_STAGE_1_INPUT": "input",
    "DBG_STAGE_2_SEARCH": "search",
    "DBG_STAGE_3_6_PROCESS": "process_posts",
    "DBG_STAGE_7_RANK": "ranking",
    "DBG_STAGE_8_PRESENT": "presentation",
    "DBG_GROUPS_SCAN_START": "search",
    "DBG_GROUPS_FEED_OPEN": "search",
    "DBG_FILTER_RECENT_TRY": "filters",
    "DBG_FILTER_24H_TRY": "filters",
    "DBG_POST_OPEN": "post_open",
    "DBG_POST_AI_SEND": "ai",
    "DBG_AI_SEND": "ai",
    "DBG_AI_ATTEMPT": "ai",
    "DBG_PIPELINE_DONE": "pipeline_done",
    "DBG_PIPELINE_SUMMARY": "pipeline_done",
}


@dataclass(frozen=True)
class DebugEvent:
    clock: str
    kind: str
    code: str
    message: str
    stage: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "clock": self.clock,
            "kind": self.kind,
            "code": self.code,
            "message": self.message,
            "stage": self.stage,
        }


def parse_debug_line(line: str) -> Optional[DebugEvent]:
    match = _DEBUG_LINE_RE.match(str(line or "").rstrip("\n"))
    if match is None:
        return None

    kind = match.group("kind")
    code = match.group("code")
    message = match.group("message")
    return DebugEvent(
        clock=match.group("clock"),
        kind=kind,
        code=code,
        message=message,
        stage=_infer_stage(code=code, kind=kind),
    )


def read_trace_events(
    trace_path: Path,
    *,
    cursor: int = 0,
    include_info: bool = False,
    include_technical: bool = False,
    limit: int = 400,
) -> Dict[str, Any]:
    normalized_cursor = max(0, int(cursor))
    path = trace_path.expanduser()
    if not path.exists():
        return {
            "trace_exists": False,
            "trace_path": str(path),
            "cursor": 0,
            "next_cursor": 0,
            "events": [],
        }

    with path.open("rb") as handle:
        handle.seek(0, 2)
        total_size = handle.tell()
        if normalized_cursor > total_size:
            normalized_cursor = 0
        handle.seek(normalized_cursor)
        raw = handle.read()
        next_cursor = handle.tell()

    text = raw.decode("utf-8", errors="replace")
    events: List[Dict[str, str]] = []
    for line in text.splitlines():
        parsed = parse_debug_line(line)
        if parsed is None:
            continue
        if parsed.kind == "INFO" and not include_info:
            continue
        if parsed.message.lower().startswith("technical details:") and not include_technical:
            continue
        events.append(parsed.to_dict())

    if limit > 0 and len(events) > limit:
        events = events[-limit:]

    return {
        "trace_exists": True,
        "trace_path": str(path),
        "cursor": normalized_cursor,
        "next_cursor": next_cursor,
        "events": events,
    }


def _infer_stage(code: str, kind: str) -> str:
    if code in _STAGE_CODE_MAP:
        return _STAGE_CODE_MAP[code]
    if code.startswith("DBG_FILTER_"):
        return "filters"
    if code.startswith("DBG_SCAN_") or code.startswith("DBG_SCROLL_") or code.startswith("DBG_GROUPS_"):
        return "search"
    if code.startswith("DBG_POST_"):
        return "post_processing"
    if code.startswith("DBG_AI_"):
        return "ai"
    if code.startswith("ERR_") or kind == "ERROR":
        return "error"
    if kind == "RESULT":
        return "result"
    return "general"

