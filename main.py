import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from app.config.startup_validation import validate_startup_config
from app.domain.pipeline import PipelineOptions, RunStatus
from app.pipeline.runner import PipelineRunner
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
    return parser.parse_args()


def build_runtime_input(args: argparse.Namespace) -> Dict[str, Any]:
    modes_selected = [bool(args.demo), bool(args.interactive), bool(args.input_file), bool(args.query)]
    selected_modes_count = sum(modes_selected)
    if selected_modes_count > 1:
        raise ValueError("Choose exactly one input mode: --demo OR --interactive OR --input-file OR --query")

    if selected_modes_count == 0:
        return load_default_input_or_demo()
    if args.demo:
        return build_demo_input()
    if args.interactive:
        return build_interactive_input()
    if args.input_file:
        return load_input_from_file(args.input_file)
    return {"query": args.query}


def load_default_input_or_demo() -> Dict[str, Any]:
    default_input_path = Path("data") / "sample_search_input.json"
    if default_input_path.exists():
        logger.info("No input mode selected. Using default input file: %s", default_input_path)
        return load_input_from_file(str(default_input_path))
    return build_demo_input()


def build_interactive_input() -> Dict[str, Any]:
    query = input("Search query: ").strip()
    if not query:
        raise ValueError("Interactive mode requires a non-empty query")
    return {"query": query}


def load_input_from_file(path: str) -> Dict[str, Any]:
    input_path = Path(path).expanduser()
    if not input_path.exists():
        raise ValueError(f"Input file does not exist: {input_path}")

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Input file is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Input file must contain a JSON object")
    return payload


def save_result_json(result_payload: Dict[str, Any], output_path: Optional[str]) -> Path:
    if output_path:
        target = Path(output_path).expanduser()
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target = Path("data") / "reports" / f"pipeline_result_{timestamp}.json"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result_payload, ensure_ascii=True, indent=2), encoding="utf-8")
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


def main() -> int:
    args = parse_args()
    warnings = validate_startup_config(require_api_key=True, require_browser_profile=True)
    for warning in warnings:
        logger.warning(warning)

    raw_input = build_runtime_input(args)
    runner = PipelineRunner()
    result = runner.run(raw_input, PipelineOptions(max_posts=args.max_posts))
    payload = result.to_dict()
    output_path = save_result_json(payload, args.output_json)
    print_summary(payload)
    logger.info("Saved JSON report to %s", output_path)

    status = result.run_state.status
    return 0 if status in {RunStatus.COMPLETED, RunStatus.STOPPED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
