from __future__ import annotations

from dotenv import load_dotenv

import manual_test_settings
from app.utils.debugging import configure_debugging, debug_info, debug_step
from main import run_pipeline_from_input


def main() -> int:
    load_dotenv()
    configure_debugging(bool(manual_test_settings.DEBUGGING))

    query = str(manual_test_settings.QUERY).strip()
    if not query:
        raise ValueError("manual_test_settings.py must define a non-empty QUERY value")

    debug_step("Starting manual test mode.")
    debug_info("Loading the query from manual_test_settings.py.")

    return run_pipeline_from_input(
        raw_input={"query": query},
        max_posts=int(manual_test_settings.MAX_POSTS),
        output_json=str(manual_test_settings.OUTPUT_JSON).strip() or None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
