import os
from datetime import datetime
from typing import Optional


_override_enabled: Optional[bool] = None


def configure_debugging(enabled: Optional[bool]) -> None:
    global _override_enabled
    if enabled is None:
        _override_enabled = None
        return

    _override_enabled = bool(enabled)
    os.environ["DEBUGGING"] = "true" if enabled else "false"


def is_debugging_enabled() -> bool:
    if _override_enabled is not None:
        return _override_enabled
    return _is_truthy(os.getenv("DEBUGGING", "false"))


def debug_info(message: str) -> None:
    _emit("INFO", message)


def debug_step(message: str) -> None:
    _emit("STEP", message)


def debug_warning(message: str) -> None:
    _emit("WARN", message)


def debug_error(message: str) -> None:
    _emit("ERROR", message)


def _emit(kind: str, message: str) -> None:
    if not is_debugging_enabled():
        return

    timestamp = datetime.now().strftime("%H:%M:%S")
    text = str(message).strip()
    print(f"[DEBUGGING {timestamp}] {kind} | {text}", flush=True)


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
