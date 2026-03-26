from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from app.domain.pipeline import PipelineOptions
from app.entrypoints.cli import (
    build_demo_input,
    build_interactive_input,
    load_input_from_file,
    run_pipeline_from_input,
)
from app.utils.app_errors import make_app_error, normalize_app_error
from app.utils.debugging import (
    close_debugging,
    configure_debugging,
    debug_app_error,
    debug_info,
    debug_result,
    debug_step,
    get_debug_trace_file_path,
    is_debugging_enabled,
)
import settings


def _optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return int(value)


def _apply_env_override(name: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        os.environ[name] = "true" if value else "false"
        return
    text = str(value).strip()
    if not text:
        return
    os.environ[name] = text


def _apply_runtime_env_overrides() -> None:
    _apply_env_override("AI_PROVIDER", settings.AI_PROVIDER_OVERRIDE)
    _apply_env_override("GROQ_MODEL_NAME", settings.GROQ_MODEL_NAME_OVERRIDE)
    _apply_env_override("GEMINI_MODEL_NAME", settings.GEMINI_MODEL_NAME_OVERRIDE)
    _apply_env_override("AI_TIMEOUT_SECONDS", settings.AI_TIMEOUT_SECONDS_OVERRIDE)
    _apply_env_override("AI_RETRY_ATTEMPTS", settings.AI_RETRY_ATTEMPTS_OVERRIDE)
    _apply_env_override("AI_RETRY_BACKOFF_SECONDS", settings.AI_RETRY_BACKOFF_SECONDS_OVERRIDE)
    _apply_env_override("AI_MAX_OUTPUT_TOKENS", settings.AI_MAX_OUTPUT_TOKENS_OVERRIDE)
    _apply_env_override("AI_TEMPERATURE", settings.AI_TEMPERATURE_OVERRIDE)

    _apply_env_override("HEADLESS", settings.HEADLESS_OVERRIDE)
    _apply_env_override("FB_TIMEOUT_MS", settings.FB_TIMEOUT_MS_OVERRIDE)
    _apply_env_override("FB_RETRIES", settings.FB_RETRIES_OVERRIDE)
    _apply_env_override("FB_MAX_SCROLL_ROUNDS", settings.FB_MAX_SCROLL_ROUNDS_OVERRIDE)
    _apply_env_override("FB_SCROLL_PAUSE_MS", settings.FB_SCROLL_PAUSE_MS_OVERRIDE)


def _build_runtime_input():
    mode = str(settings.RUN_MODE).strip().lower()

    if mode == "demo":
        return build_demo_input(), "demo"
    if mode == "interactive":
        return build_interactive_input(), "interactive"
    if mode == "query":
        return {"query": str(settings.QUERY).strip()}, "query"
    if mode == "file":
        input_path = str(settings.INPUT_FILE).strip() or str(Path("data") / "sample_search_input.json")
        return load_input_from_file(input_path), "file"

    raise make_app_error(
        code="ERR_INPUT_MODE_INVALID",
        summary_he="RUN_MODE בקובץ settings.py אינו תקין",
        cause_he="התקבל ערך שאינו אחד מהמצבים הנתמכים",
        action_he='הגדר RUN_MODE לאחד מהערכים: "file", "query", "interactive", "demo"',
        technical_details=f"RUN_MODE={settings.RUN_MODE}",
    )


def main() -> int:
    configure_debugging(bool(settings.DEBUGGING), _optional_text(getattr(settings, "DEBUG_TRACE_FILE", None)))

    try:
        load_dotenv()
        _apply_runtime_env_overrides()
        raw_input, source = _build_runtime_input()

        debug_step("DBG_RUN_START", f"מתחיל ריצה חדשה מ-start.py במצב: {source}.")
        debug_info("DBG_DEBUG_MODE", f"מצב DEBUGGING הוא {'פעיל' if settings.DEBUGGING else 'כבוי'}.")

        pipeline_options = PipelineOptions(
            max_posts=int(settings.MAX_POSTS),
            continue_on_post_error=bool(settings.CONTINUE_ON_POST_ERROR),
            stop_after_post_errors=_optional_int(settings.STOP_AFTER_POST_ERRORS),
            save_run_history=bool(settings.SAVE_RUN_HISTORY),
        )

        exit_code = run_pipeline_from_input(
            raw_input=raw_input,
            max_posts=pipeline_options.max_posts,
            output_json=_optional_text(settings.OUTPUT_JSON),
            pipeline_options=pipeline_options,
        )
        if is_debugging_enabled():
            trace_path = get_debug_trace_file_path()
            if trace_path:
                debug_result("DBG_TRACE_FILE", f"קובץ debug trace נשמר אל: {trace_path}")
        debug_result("DBG_RUN_END", f"הריצה הסתיימה עם קוד יציאה {exit_code}.")
        return exit_code
    except Exception as exc:  # noqa: BLE001
        app_error = normalize_app_error(
            exc,
            default_code="ERR_PIPELINE_UNEXPECTED",
            default_summary_he="הריצה הופסקה בגלל שגיאה לא צפויה",
            default_cause_he="רכיב פנימי זרק חריגה שלא טופלה מראש",
            default_action_he="בדוק debug trace ו-app.log ונסה שוב",
        )
        debug_app_error(app_error)
        return 1
    finally:
        close_debugging()


if __name__ == "__main__":
    raise SystemExit(main())
