from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

import start_settings
from app.utils.debugging import configure_debugging, debug_info, debug_step
from main import build_demo_input, build_interactive_input, load_input_from_file, run_pipeline_from_input


def _build_runtime_input():
    mode = str(start_settings.RUN_MODE).strip().lower()

    if mode == "demo":
        return build_demo_input(), "demo"
    if mode == "interactive":
        return build_interactive_input(), "interactive"
    if mode == "query":
        return {"query": str(start_settings.QUERY).strip()}, "query"
    if mode == "file":
        input_path = str(start_settings.INPUT_FILE).strip() or str(Path("data") / "sample_search_input.json")
        return load_input_from_file(input_path), "file"

    raise ValueError("RUN_MODE must be one of: file, query, interactive, demo")


def main() -> int:
    load_dotenv()
    configure_debugging(bool(start_settings.DEBUGGING))

    raw_input, source = _build_runtime_input()
    debug_step(f"Starting the program from start.py using run mode: {source}.")
    debug_info(f"Debugging mode is {'on' if start_settings.DEBUGGING else 'off'}.")

    return run_pipeline_from_input(
        raw_input=raw_input,
        max_posts=int(start_settings.MAX_POSTS),
        output_json=str(start_settings.OUTPUT_JSON).strip() or None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
