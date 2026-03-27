#!/usr/bin/env python3
"""Start the local UI server and optionally open the dashboard in a browser."""

from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.server import start_ui_server


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_BROWSER_DELAY_SECONDS = 1.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the local dashboard server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind the UI server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind the UI server")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the UI server without opening a browser tab",
    )
    parser.add_argument(
        "--browser-delay",
        type=float,
        default=DEFAULT_BROWSER_DELAY_SECONDS,
        help="Seconds to wait before opening the browser tab",
    )
    return parser.parse_args()


def _open_browser(host: str, port: int, delay_seconds: float) -> None:
    time.sleep(max(0.0, float(delay_seconds)))
    url = f"http://{host}:{port}"
    print(f"Opening browser at {url} ...")
    webbrowser.open(url)


def main() -> int:
    args = parse_args()
    if not args.no_browser:
        threading.Thread(
            target=_open_browser,
            args=(args.host, int(args.port), float(args.browser_delay)),
            daemon=True,
        ).start()

    print(f"Starting UI server on http://{args.host}:{int(args.port)}")
    start_ui_server(host=args.host, port=int(args.port), root_dir=PROJECT_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
