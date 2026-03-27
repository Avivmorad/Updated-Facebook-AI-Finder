from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from app.browser.step_debug import load_step_events
from app.config.browser import BrowserConfig
from app.presentation.run_history_store import RunHistoryStore
from app.ui.debug_trace import read_trace_events
from app.ui.run_manager import PipelineRunManager


@dataclass
class UIContext:
    static_dir: Path
    report_path: Path
    browser_config: BrowserConfig
    run_manager: PipelineRunManager
    run_history_store: RunHistoryStore


def start_ui_server(*, host: str, port: int, root_dir: Path) -> None:
    static_dir = root_dir / "app" / "ui" / "static"
    report_path = root_dir / "data" / "reports" / "latest.json"
    run_manager = PipelineRunManager(
        root_dir=root_dir,
        output_json_path=report_path,
        trace_file_path=root_dir / "data" / "logs" / "debug_trace.txt",
    )
    context = UIContext(
        static_dir=static_dir,
        report_path=report_path,
        browser_config=BrowserConfig(),
        run_manager=run_manager,
        run_history_store=RunHistoryStore(),
    )
    handler_cls = _build_handler(context)
    server = ThreadingHTTPServer((host, port), handler_cls)
    print(f"UI server listening on http://{host}:{port}", flush=True)
    server.serve_forever()


def _build_handler(context: UIContext) -> type[BaseHTTPRequestHandler]:
    class UIHandler(BaseHTTPRequestHandler):
        server_version = "FacebookAIFinderUI/1.0"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query, keep_blank_values=True)

            if path in {"/", "/index.html"}:
                self._serve_static_file("index.html", "text/html; charset=utf-8")
                return
            if path == "/app.js":
                self._serve_static_file("app.js", "application/javascript; charset=utf-8")
                return
            if path == "/styles.css":
                self._serve_static_file("styles.css", "text/css; charset=utf-8")
                return
            if path == "/api/run/status":
                self._send_json(context.run_manager.get_status())
                return
            if path == "/api/report/latest":
                self._handle_latest_report()
                return
            if path == "/api/runs":
                self._handle_runs(query)
                return
            if path == "/api/debug":
                self._handle_debug(query)
                return
            if path == "/api/browser-steps":
                self._handle_browser_steps(query)
                return
            if path.startswith("/api/browser-step-image/"):
                self._handle_browser_step_image(path)
                return
            if path == "/api/health":
                self._send_json({"ok": True, "status": "healthy"})
                return

            self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/run":
                self._handle_run_start()
                return
            if parsed.path == "/api/run/stop":
                self._handle_run_stop()
                return
            self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, fmt: str, *args: object) -> None:
            _ = fmt
            _ = args
            # Keep UI terminal output clean.
            return

        def _handle_run_start(self) -> None:
            payload, error_message = self._read_json_body()
            if error_message:
                self._send_json({"error": error_message}, status=HTTPStatus.BAD_REQUEST)
                return

            query = str(payload.get("query") or "").strip()
            try:
                max_posts = int(payload.get("max_posts", 20))
            except (TypeError, ValueError):
                self._send_json({"error": "max_posts must be a number"}, status=HTTPStatus.BAD_REQUEST)
                return
            browser_watch = _parse_bool(str(payload.get("browser_watch", "false")), default=False)
            tracking_enabled = _parse_bool(str(payload.get("tracking_enabled", "false")), default=False)
            debug_log_enabled = _parse_bool(str(payload.get("debug_log_enabled", "false")), default=False)
            try:
                slow_mo_ms = int(payload.get("slow_mo_ms", 0))
            except (TypeError, ValueError):
                self._send_json({"error": "slow_mo_ms must be a number"}, status=HTTPStatus.BAD_REQUEST)
                return

            ok, message, status_payload = context.run_manager.start_run(
                query=query,
                max_posts=max_posts,
                tracking_enabled=tracking_enabled,
                debug_log_enabled=debug_log_enabled,
                show_browser=browser_watch,
                slow_mo_ms=slow_mo_ms,
            )
            if ok:
                self._send_json({"ok": True, "message": message, "status": status_payload})
                return

            status_code = HTTPStatus.CONFLICT
            if message in {"query is required", "max_posts must be > 0"}:
                status_code = HTTPStatus.BAD_REQUEST
            self._send_json({"ok": False, "error": message, "status": status_payload}, status=status_code)

        def _handle_run_stop(self) -> None:
            ok, message, status_payload = context.run_manager.stop_run()
            if ok:
                self._send_json({"ok": True, "message": message, "status": status_payload})
                return
            self._send_json({"ok": False, "error": message, "status": status_payload}, status=HTTPStatus.CONFLICT)

        def _handle_latest_report(self) -> None:
            payload = _read_json_file(context.report_path)
            if payload is None:
                self._send_json(
                    {"error": "latest report not found", "path": str(context.report_path)},
                    status=HTTPStatus.NOT_FOUND,
                )
                return
            self._send_json({"report": payload, "path": str(context.report_path)})

        def _handle_runs(self, query: Dict[str, List[str]]) -> None:
            limit = _parse_positive_int(query.get("limit", ["20"])[0], default=20)
            items = context.run_history_store.load_runs(limit=limit)
            summarized = [_summarize_run(item) for item in items]
            self._send_json({"runs": summarized, "count": len(summarized)})

        def _handle_debug(self, query: Dict[str, List[str]]) -> None:
            cursor = _parse_positive_int(query.get("cursor", ["0"])[0], default=0)
            limit = _parse_positive_int(query.get("limit", ["400"])[0], default=400)
            include_info = _parse_bool(query.get("include_info", ["false"])[0], default=False)
            include_technical = _parse_bool(query.get("include_technical", ["false"])[0], default=False)
            payload = read_trace_events(
                context.run_manager.trace_file_path,
                cursor=cursor,
                include_info=include_info,
                include_technical=include_technical,
                limit=limit,
            )
            payload["status"] = context.run_manager.get_status()
            self._send_json(payload)

        def _handle_browser_steps(self, query: Dict[str, List[str]]) -> None:
            limit = _parse_positive_int(query.get("limit", ["40"])[0], default=40)
            payload = load_step_events(context.browser_config, limit=limit)
            for item in payload.get("events", []):
                image_name = str(item.get("image_name", "")).strip()
                if image_name:
                    item["image_url"] = f"/api/browser-step-image/{image_name}"
            self._send_json(payload)

        def _handle_browser_step_image(self, path: str) -> None:
            image_name = path.replace("/api/browser-step-image/", "", 1).strip()
            if not image_name:
                self._send_json({"error": "image name is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            safe_name = Path(image_name).name
            target = Path(context.browser_config.step_debug_dir).expanduser() / safe_name
            if not target.exists():
                self._send_json({"error": "image not found"}, status=HTTPStatus.NOT_FOUND)
                return
            try:
                raw = target.read_bytes()
            except OSError as exc:
                self._send_json({"error": f"failed reading image: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _serve_static_file(self, relative_path: str, content_type: str) -> None:
            target = context.static_dir / relative_path
            if not target.exists():
                self._send_json({"error": "static file not found", "path": str(target)}, status=HTTPStatus.NOT_FOUND)
                return
            try:
                raw = target.read_bytes()
            except OSError as exc:
                self._send_json({"error": f"failed reading static file: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json_body(self) -> tuple[Dict[str, Any], str]:
            content_length_raw = self.headers.get("Content-Length", "0").strip()
            try:
                content_length = int(content_length_raw)
            except ValueError:
                return {}, "invalid content length"
            if content_length <= 0:
                return {}, "request body is required"

            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}, "request body must be valid JSON"
            if not isinstance(payload, dict):
                return {}, "request body must be a JSON object"
            return payload, ""

        def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return UIHandler


def _read_json_file(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _parse_bool(value: str, *, default: bool) -> bool:
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_positive_int(value: str, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < 0:
        return default
    return parsed


def _summarize_run(run: Dict[str, Any]) -> Dict[str, Any]:
    run_state = run.get("run_state", {}) if isinstance(run, dict) else {}
    progress = run_state.get("progress", {}) if isinstance(run_state, dict) else {}
    runtime = run_state.get("runtime", {}) if isinstance(run_state, dict) else {}
    presented = run.get("presented_results", {}) if isinstance(run, dict) else {}
    request_payload = run.get("request_payload", {}) if isinstance(run, dict) else {}

    status = str(run_state.get("status", "unknown"))
    stop_reason = run_state.get("stop_reason")
    total_results = int(presented.get("total_results", 0) or 0) if isinstance(presented, dict) else 0

    return {
        "run_id": str(run.get("run_id", "")),
        "saved_at": str(run.get("saved_at", "")),
        "status": status,
        "query": str(request_payload.get("query", "")) if isinstance(request_payload, dict) else "",
        "total_results": total_results,
        "processed_posts": int(progress.get("processed_posts", 0) or 0) if isinstance(progress, dict) else 0,
        "max_posts": int(progress.get("max_posts", 0) or 0) if isinstance(progress, dict) else 0,
        "elapsed_seconds": float(runtime.get("elapsed_seconds", 0.0) or 0.0) if isinstance(runtime, dict) else 0.0,
        "stop_reason": str(stop_reason or ""),
    }
