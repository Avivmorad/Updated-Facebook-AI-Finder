from __future__ import annotations

import argparse
from pathlib import Path

from app.ui.server import start_ui_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local interactive UI for Facebook Groups Post Finder & Matcher")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the UI server")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind the UI server")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[2]
    start_ui_server(host=args.host, port=int(args.port), root_dir=project_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

