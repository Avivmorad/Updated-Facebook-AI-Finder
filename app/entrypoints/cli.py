import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from app.config.startup_validation import validate_startup_config
from app.domain.pipeline import PipelineOptions, RunStatus
from app.pipeline.runner import PipelineRunner
from app.utils.app_errors import make_app_error, normalize_app_error
from app.utils.debugging import (
    close_debugging,
    configure_debugging,
    debug_app_error,
    debug_found,
    debug_info,
    debug_result,
    debug_step,
    debug_warning,
    get_debug_trace_file_path,
    is_debugging_enabled,
)
from app.utils.logger import get_logger


logger = get_logger(__name__)
load_dotenv()


def build_demo_input() -> Dict[str, Any]:
    return {"query": "iphone 13"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Facebook Groups Post Finder & Matcher.")
    parser.add_argument("--demo", action="store_true", help="Run with built-in demo input")
    parser.add_argument("--interactive", action="store_true", help="Prompt for a query")
    parser.add_argument("--input-file", help="Path to a JSON file containing query input")
    parser.add_argument("--query", help="Search query text")
    parser.add_argument("--max-posts", type=int, default=20)
    parser.add_argument("--output-json", help="Optional path for saving run result JSON")
    parser.add_argument("--debugging", action="store_true", help="Print a detailed human-readable run trace to the terminal")
    return parser.parse_args()


def build_runtime_input(args: argparse.Namespace) -> Tuple[Dict[str, Any], str]:
    modes_selected = [bool(args.demo), bool(args.interactive), bool(args.input_file), bool(args.query)]
    selected_modes_count = sum(modes_selected)
    if selected_modes_count > 1:
        raise make_app_error(
            code="ERR_INPUT_MODE_INVALID",
            summary_he="נבחרו כמה מצבי קלט יחד",
            cause_he="אפשר לבחור רק מקור קלט אחד בכל ריצה",
            action_he="בחר רק אחד: --demo או --interactive או --input-file או --query",
        )

    if selected_modes_count == 0:
        return load_default_input_or_demo()
    if args.demo:
        return build_demo_input(), "demo"
    if args.interactive:
        return build_interactive_input(), "interactive"
    if args.input_file:
        return load_input_from_file(args.input_file), f"file:{args.input_file}"
    return {"query": args.query}, "query"


def load_default_input_or_demo() -> Tuple[Dict[str, Any], str]:
    default_input_path = Path("data") / "sample_search_input.json"
    if default_input_path.exists():
        logger.info("No input mode selected. Using default input file: %s", default_input_path)
        return load_input_from_file(str(default_input_path)), f"default-file:{default_input_path}"
    return build_demo_input(), "default-demo"


def build_interactive_input() -> Dict[str, Any]:
    query = input("Search query: ").strip()
    if not query:
        raise make_app_error(code="ERR_INPUT_QUERY_MISSING")
    return {"query": query}


def load_input_from_file(path: str) -> Dict[str, Any]:
    input_path = Path(path).expanduser()
    if not input_path.exists():
        raise make_app_error(
            code="ERR_INPUT_FILE_NOT_FOUND",
            technical_details=f"path={input_path}",
        )

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise make_app_error(
            code="ERR_INPUT_JSON_INVALID",
            technical_details=f"path={input_path} error={exc}",
        ) from exc

    if not isinstance(payload, dict):
        raise make_app_error(
            code="ERR_INPUT_JSON_INVALID",
            summary_he="קובץ הקלט חייב להכיל אובייקט JSON",
            cause_he="הקובץ נטען אבל הטיפוס העליון אינו object",
            action_he='עדכן את הקובץ כך שייראה למשל כך: {"query":"iphone 13"}',
            technical_details=f"path={input_path}",
        )
    return payload


def save_result_json(result_payload: Dict[str, Any], output_path: Optional[str]) -> Path:
    if output_path:
        target = Path(output_path).expanduser()
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target = Path("data") / "reports" / f"pipeline_result_{timestamp}.json"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    except OSError as exc:
        raise make_app_error(
            code="ERR_RESULT_SAVE_FAILED",
            technical_details=f"path={target} error={exc}",
        ) from exc
    return target


def print_summary(result_payload: Dict[str, Any]) -> None:
    presented = result_payload.get("presented_results", {})
    print(f"Total results: {presented.get('total_results', 0)}")
    for item in presented.get("top_results", []):
        print(
            "- score={score:.2f} | link={link} | summary={summary}".format(
                score=float(item.get("match_score", 0.0)),
                link=item.get("post_link", ""),
                summary=item.get("short_summary", ""),
            )
        )


def run_pipeline_from_input(
    raw_input: Dict[str, Any],
    max_posts: int,
    output_json: Optional[str] = None,
    pipeline_options: Optional[PipelineOptions] = None,
) -> int:
    debug_step("DBG_STARTUP_CHECK", "בודק הגדרות התחלה לפני תחילת הריצה.")
    warnings = validate_startup_config(require_api_key=True, require_browser_profile=True)
    if warnings:
        for warning in warnings:
            logger.warning(warning)
            debug_warning("DBG_STARTUP_WARN", f"אזהרת התחלה: {warning}")
    else:
        debug_found("DBG_STARTUP_OK", "הגדרות התחלה נראות תקינות.")

    options = pipeline_options or PipelineOptions(max_posts=max_posts)

    query_text = str(raw_input.get("query") or raw_input.get("main_text") or "").strip()
    if query_text:
        debug_info("DBG_QUERY_VALUE", f'שאילתת החיפוש: "{query_text}"')
    debug_info("DBG_MAX_POSTS", f"מקסימום פוסטים לבדיקה בריצה: {options.max_posts}.")

    runner = PipelineRunner()
    result = runner.run(raw_input, options)
    payload = result.to_dict()
    output_path = save_result_json(payload, output_json)

    print_summary(payload)
    print(f"Saved JSON report: {output_path}")
    debug_result("DBG_OUTPUT_SAVED", f"קובץ התוצאות נשמר אל: {output_path}")
    if is_debugging_enabled():
        trace_path = get_debug_trace_file_path()
        if trace_path:
            debug_result("DBG_TRACE_FILE", f"קובץ debug trace נשמר אל: {trace_path}")
    logger.info("Saved JSON report to %s", output_path)

    status = result.run_state.status
    return 0 if status in {RunStatus.COMPLETED, RunStatus.STOPPED} else 1


def main() -> int:
    args = parse_args()
    configure_debugging(args.debugging, os.getenv("DEBUG_TRACE_FILE"))

    try:
        raw_input, input_source = build_runtime_input(args)
        debug_step("DBG_CLI_START", f"הפעלת CLI עם מקור קלט: {input_source}.")
        return run_pipeline_from_input(raw_input=raw_input, max_posts=args.max_posts, output_json=args.output_json)
    except Exception as exc:  # noqa: BLE001
        app_error = normalize_app_error(
            exc,
            default_code="ERR_PIPELINE_UNEXPECTED",
            default_summary_he="הרצת CLI הופסקה בגלל שגיאה",
            default_cause_he="נזרקה חריגה שלא טופלה ספציפית",
            default_action_he="בדוק debug trace ו-app.log ונסה שוב",
        )
        debug_app_error(app_error)
        return 1
    finally:
        close_debugging()


if __name__ == "__main__":
    raise SystemExit(main())
