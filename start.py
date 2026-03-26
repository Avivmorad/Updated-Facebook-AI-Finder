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
from app.utils.debugging import configure_debugging, debug_info, debug_step
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

    raise ValueError("RUN_MODE must be one of: file, query, interactive, demo")


def main() -> int:
    load_dotenv()
    _apply_runtime_env_overrides()
    configure_debugging(bool(settings.DEBUGGING))

    raw_input, source = _build_runtime_input()
    debug_step(f"Starting the program from start.py using run mode: {source}.")
    debug_info(f"Debugging mode is {'on' if settings.DEBUGGING else 'off'}.")

    pipeline_options = PipelineOptions(
        max_posts=int(settings.MAX_POSTS),
        continue_on_post_error=bool(settings.CONTINUE_ON_POST_ERROR),
        stop_after_post_errors=_optional_int(settings.STOP_AFTER_POST_ERRORS),
        save_run_history=bool(settings.SAVE_RUN_HISTORY),
    )

    return run_pipeline_from_input(
        raw_input=raw_input,
        max_posts=pipeline_options.max_posts,
        output_json=_optional_text(settings.OUTPUT_JSON),
        pipeline_options=pipeline_options,
    )


if __name__ == "__main__":
    raise SystemExit(main())
