#!/usr/bin/env python3
"""Simple launcher for Facebook Groups Post Finder & Matcher."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def _run(command: list[str]) -> int:
    print("\n>>", " ".join(command))
    completed = subprocess.run(command, cwd=str(ROOT), check=False)
    return int(completed.returncode)


def _run_live_gate(output_json: str) -> int:
    commands = [
        [PYTHON, "-m", "pytest", "-c", "tests/pytest.ini", "-q"],
        [PYTHON, "scripts/doctor.py"],
        [PYTHON, "scripts/doctor.py", "--check-facebook-session"],
        [PYTHON, "start.py"],
    ]
    for command in commands:
        code = _run(command)
        if code != 0:
            return code

    reports_dir = ROOT / "data" / "reports"
    trace_file = ROOT / "data" / "logs" / "debug_trace.txt"
    has_report = reports_dir.exists() and any(reports_dir.glob("*.json"))
    if not has_report:
        print("[FAIL] Live gate expected at least one JSON report in data/reports")
        return 1
    if not trace_file.exists():
        print("[FAIL] Live gate expected debug trace file at data/logs/debug_trace.txt")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Quick launcher for Facebook Groups Post Finder & Matcher")
    parser.add_argument(
        "--mode",
        choices=["run", "demo", "interactive", "file", "doctor", "doctor-session", "test", "start", "verify-live"],
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
        help="Output JSON path for pipeline modes",
    )
    args = parser.parse_args()

    if args.mode == "doctor":
        return _run([PYTHON, "scripts/doctor.py"])
    if args.mode == "doctor-session":
        return _run([PYTHON, "scripts/doctor.py", "--check-facebook-session"])
    if args.mode == "test":
        return _run_live_gate(args.output_json)
    if args.mode == "verify-live":
        return _run_live_gate(args.output_json)
    if args.mode == "start":
        return _run([PYTHON, "start.py"])
    if args.mode == "demo":
        return _run([PYTHON, "-m", "app.entrypoints.cli", "--demo", "--output-json", args.output_json])
    if args.mode == "interactive":
        return _run([PYTHON, "-m", "app.entrypoints.cli", "--interactive"])
    if args.mode == "file":
        return _run([PYTHON, "-m", "app.entrypoints.cli", "--input-file", args.input_file, "--output-json", args.output_json])

    return _run([PYTHON, "-m", "app.entrypoints.cli", "--input-file", args.input_file, "--output-json", args.output_json])


if __name__ == "__main__":
    raise SystemExit(main())
