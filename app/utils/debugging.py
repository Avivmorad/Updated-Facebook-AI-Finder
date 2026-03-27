from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.utils.app_errors import AppError
from app.utils.logger import get_logger


DEFAULT_TRACE_FILE = str(Path("data") / "logs" / "debug_trace.txt")

_TRUTHY_VALUES = {"1", "true", "yes", "on"}
_logger = get_logger(__name__)
_override_enabled: Optional[bool] = None
_trace_writer: Optional["_TraceWriter"] = None


@dataclass
class _TraceWriter:
    path: Path
    handle: Optional[object] = None
    write_failed: bool = False
    warned: bool = False

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("w", encoding="utf-8")
        self.write_failed = False
        self.warned = False

    def write_line(self, line: str) -> None:
        if self.handle is None or self.write_failed:
            return
        try:
            self.handle.write(line + "\n")
            self.handle.flush()
        except OSError:
            self.write_failed = True

    def close(self) -> None:
        if self.handle is None:
            return
        try:
            self.handle.close()
        finally:
            self.handle = None


def configure_debugging(enabled: Optional[bool], trace_file_path: Optional[str] = None) -> None:
    global _override_enabled

    _override_enabled = None if enabled is None else bool(enabled)
    if enabled is not None:
        os.environ["DEBUGGING"] = "true" if enabled else "false"

    configure_debug_trace_file(trace_file_path)


def configure_debug_trace_file(trace_file_path: Optional[str]) -> None:
    global _trace_writer

    _close_writer()
    if not is_debugging_enabled():
        return

    resolved = (trace_file_path or "").strip() or DEFAULT_TRACE_FILE
    writer = _TraceWriter(path=Path(resolved).expanduser())
    try:
        writer.open()
        _trace_writer = writer
    except OSError as exc:
        _trace_writer = None
        _logger.warning("Failed to initialize debug trace file: %s", str(exc))


def close_debugging() -> None:
    _close_writer()


def get_debug_trace_file_path() -> Optional[str]:
    writer = _trace_writer
    if writer is None:
        return None
    return str(writer.path)


def is_debugging_enabled() -> bool:
    if _override_enabled is not None:
        return _override_enabled
    value = str(os.getenv("DEBUGGING", "false")).strip().lower()
    return value in _TRUTHY_VALUES


def debug_step(code: str, message: str) -> None:
    _emit("STEP", code, message)


def debug_info(code: str, message: str) -> None:
    _emit("INFO", code, message)


def debug_found(code: str, message: str) -> None:
    _emit("FOUND", code, message)


def debug_missing(code: str, message: str) -> None:
    _emit("MISSING", code, message)


def debug_warning(code: str, message: str) -> None:
    _emit("WARN", code, message)


def debug_error(code: str, message: str) -> None:
    _emit("ERROR", code, message)


def debug_result(code: str, message: str) -> None:
    _emit("RESULT", code, message)


def debug_app_error(error: AppError, *, include_technical_details: bool = True) -> None:
    debug_error(error.code, error.summary_he)
    debug_info(error.code, f"Cause: {error.cause_he}")
    debug_info(error.code, f"Action: {error.action_he}")
    if include_technical_details and error.technical_details:
        debug_info(error.code, f"Technical details: {error.technical_details}")


def _emit(kind: str, code: str, message: str) -> None:
    if not is_debugging_enabled():
        return

    normalized_code = str(code).strip() or "DBG_GENERAL"
    normalized_message = str(message).strip() or "-"
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[DEBUG {timestamp}] {kind} {normalized_code} | {normalized_message}"
    _safe_print(line)

    writer = _trace_writer
    if writer is None:
        return

    writer.write_line(line)
    if writer.write_failed and not writer.warned:
        writer.warned = True
        _logger.warning("Failed to write debug trace line; continuing with terminal output only.")
        warn_line = (
            f"[DEBUG {timestamp}] WARN ERR_DEBUG_TRACE_SAVE_FAILED | "
            "Failed writing debug trace file, continuing with terminal output only."
        )
        _safe_print(warn_line)


def _close_writer() -> None:
    global _trace_writer

    if _trace_writer is not None:
        _trace_writer.close()
    _trace_writer = None


def _safe_print(line: str) -> None:
    try:
        print(line, flush=True)
        return
    except UnicodeEncodeError:
        escaped = line.encode("ascii", "backslashreplace").decode("ascii")
        try:
            print(escaped, flush=True)
            return
        except OSError:
            pass
    except OSError:
        pass

    try:
        import sys

        escaped = line.encode("ascii", "backslashreplace").decode("ascii")
        sys.stderr.write(escaped + "\n")
        sys.stderr.flush()
    except OSError:
        # Keep runtime alive even when terminal streams become unavailable.
        _logger.warning("Debug output stream is unavailable; skipping terminal debug line.")
