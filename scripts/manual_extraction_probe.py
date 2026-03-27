#!/usr/bin/env python3
"""Run direct post extraction for a local list of Facebook post URLs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.search_service import SearchService
from app.utils.debugging import close_debugging, configure_debugging, debug_info, debug_result, debug_step


def _load_post_links(path: Path) -> List[str]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [str(item).strip() for item in payload if str(item).strip()]
    if isinstance(payload, dict):
        values = payload.get("post_links", [])
        if isinstance(values, list):
            return [str(item).strip() for item in values if str(item).strip()]
    return []


def _save_report(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual extraction probe using local post links JSON")
    parser.add_argument("--links-file", default="data/local/manual_post_links.json")
    parser.add_argument("--output-json", default="data/reports/manual_probe_latest.json")
    parser.add_argument("--debugging", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    configure_debugging(args.debugging, "data/logs/debug_trace.txt")

    try:
        links_path = Path(args.links_file).expanduser()
        links = _load_post_links(links_path)
        if not links:
            template = {"post_links": ["https://www.facebook.com/share/p/EXAMPLE/"]}
            links_path.parent.mkdir(parents=True, exist_ok=True)
            links_path.write_text(json.dumps(template, ensure_ascii=True, indent=2), encoding="utf-8")
            print(f"No links found. Created template file: {links_path}")
            return 1

        debug_step("DBG_MANUAL_PROBE_START", f"Starting manual extraction probe for {len(links)} link(s).")
        service = SearchService()
        extracted = service.collect_posts_from_links(links)

        success_items = [item for item in extracted if bool(item.get("extraction_success", False))]
        failed_items = [item for item in extracted if not bool(item.get("extraction_success", False))]
        debug_info(
            "DBG_MANUAL_PROBE_SUMMARY",
            f"Manual probe extracted {len(success_items)} success and {len(failed_items)} failed items.",
        )

        report = {
            "input_links": links,
            "total": len(extracted),
            "success_count": len(success_items),
            "failure_count": len(failed_items),
            "items": extracted,
        }
        output_path = Path(args.output_json).expanduser()
        _save_report(output_path, report)
        debug_result("DBG_MANUAL_PROBE_SAVED", f"Manual extraction probe report saved: {output_path}")
        print(f"Saved manual extraction probe report: {output_path}")
        return 0
    finally:
        close_debugging()


if __name__ == "__main__":
    raise SystemExit(main())
