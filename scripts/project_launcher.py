#!/usr/bin/env python3
"""Launch common project workflows from one place."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
REPORTS_DIR = ROOT / "data" / "reports"


def _run(command: list[str]) -> int:
    print("\n>>", " ".join(command))
    completed = subprocess.run(command, cwd=str(ROOT), check=False)
    return int(completed.returncode)


def _snapshot_report_files() -> dict[Path, int]:
    snapshot: dict[Path, int] = {}
    if not REPORTS_DIR.exists():
        return snapshot
    for path in REPORTS_DIR.glob("*.json"):
        try:
            snapshot[path.resolve()] = path.stat().st_mtime_ns
        except OSError:
            continue
    return snapshot


def _find_updated_report(snapshot: dict[Path, int]) -> Path | None:
    if not REPORTS_DIR.exists():
        return None

    latest_path: Path | None = None
    latest_mtime = -1
    for path in REPORTS_DIR.glob("*.json"):
        try:
            resolved = path.resolve()
            current_mtime = path.stat().st_mtime_ns
        except OSError:
            continue
        if current_mtime <= snapshot.get(resolved, -1):
            continue
        if current_mtime > latest_mtime:
            latest_path = path
            latest_mtime = current_mtime
    return latest_path


def _report_is_valid(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    return isinstance(payload.get("run_state"), dict) and isinstance(payload.get("presented_results"), dict)


def _run_live_gate() -> int:
    report_snapshot = _snapshot_report_files()
    commands = [
        [PYTHON, "-m", "pytest", "-c", "pytest.ini", "-q"],
        [PYTHON, "scripts/check_runtime_setup.py"],
        [PYTHON, "scripts/check_runtime_setup.py", "--check-facebook-session"],
        [PYTHON, "start.py"],
    ]
    for command in commands:
        code = _run(command)
        if code != 0:
            return code

    updated_report = _find_updated_report(report_snapshot)
    if updated_report is None:
        print("[FAIL] Live gate expected a new or updated JSON report in data/reports")
        return 1
    if not _report_is_valid(updated_report):
        print(f"[FAIL] Live gate found an invalid report: {updated_report}")
        return 1
    print(f"[OK] Live gate verified report: {updated_report}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch common project workflows")
    parser.add_argument(
        "--mode",
        choices=[
            "run",
            "demo",
            "interactive",
            "file",
            "doctor",
            "doctor-session",
            "test",
            "start",
            "verify-live",
            "probe-links",
            "ui",
        ],
        default="run",
        help="What to run",
    )
    parser.add_argument(
        "--input-file",
        default="data/sample_search_input.json",
        help="Input JSON path for --mode file/run",
    )
    parser.add_argument(
        "--output-json",
        default="data/reports/latest.json",
        help="Output JSON path for CLI pipeline modes",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind UI server for --mode ui")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind UI server for --mode ui")
    args = parser.parse_args()

    if args.mode == "doctor":
        return _run([PYTHON, "scripts/check_runtime_setup.py"])
    if args.mode == "doctor-session":
        return _run([PYTHON, "scripts/check_runtime_setup.py", "--check-facebook-session"])
    if args.mode == "test":
        return _run_live_gate()
    if args.mode == "verify-live":
        return _run_live_gate()
    if args.mode == "start":
        return _run([PYTHON, "start.py"])
    if args.mode == "probe-links":
        return _run([PYTHON, "scripts/extract_posts_from_saved_links.py", "--debugging"])
    if args.mode == "ui":
        return _run([PYTHON, "-m", "app.entrypoints.ui", "--host", args.host, "--port", str(args.port)])
    if args.mode == "demo":
        return _run([PYTHON, "-m", "app.entrypoints.cli", "--demo", "--output-json", args.output_json])
    if args.mode == "interactive":
        return _run([PYTHON, "-m", "app.entrypoints.cli", "--interactive"])
    if args.mode == "file":
        return _run([PYTHON, "-m", "app.entrypoints.cli", "--input-file", args.input_file, "--output-json", args.output_json])

    return _run([PYTHON, "-m", "app.entrypoints.cli", "--input-file", args.input_file, "--output-json", args.output_json])


if __name__ == "__main__":
    raise SystemExit(main())


