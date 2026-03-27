from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ManagedRunState:
    status: str = "idle"
    run_id: str = ""
    query: str = ""
    max_posts: int = 20
    tracking_enabled: bool = False
    debug_log_enabled: bool = False
    show_browser: bool = False
    stop_reason: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "run_id": self.run_id,
            "query": self.query,
            "max_posts": self.max_posts,
            "tracking_enabled": self.tracking_enabled,
            "debug_log_enabled": self.debug_log_enabled,
            "show_browser": self.show_browser,
            "stop_reason": self.stop_reason,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_code": self.exit_code,
            "error": self.error,
        }


class PipelineRunManager:
    def __init__(
        self,
        *,
        root_dir: Path,
        output_json_path: Path,
        trace_file_path: Path,
        python_executable: str = sys.executable,
    ) -> None:
        self._root_dir = root_dir
        self._output_json_path = output_json_path
        self._trace_file_path = trace_file_path
        self._python_executable = python_executable
        self._lock = threading.Lock()
        self._process: Optional[subprocess.Popen[object]] = None
        self._state = ManagedRunState()
        self._stop_requested = False

    @property
    def output_json_path(self) -> Path:
        return self._output_json_path

    @property
    def trace_file_path(self) -> Path:
        return self._trace_file_path

    def get_status(self) -> Dict[str, object]:
        with self._lock:
            self._refresh_locked()
            payload = self._state.to_dict()
            payload["output_json_path"] = str(self._output_json_path)
            payload["trace_file_path"] = str(self._trace_file_path)
            payload["is_running"] = self._state.status in {"running", "stopping"}
            payload["can_stop"] = self._state.status in {"running", "stopping"}
            return payload

    def start_run(
        self,
        *,
        query: str,
        max_posts: int,
        tracking_enabled: bool = False,
        debug_log_enabled: bool = False,
        show_browser: bool = False,
        slow_mo_ms: int = 0,
    ) -> Tuple[bool, str, Dict[str, object]]:
        normalized_query = str(query or "").strip()
        if not normalized_query:
            return False, "query is required", self.get_status()

        normalized_max_posts = int(max_posts)
        if normalized_max_posts <= 0:
            return False, "max_posts must be > 0", self.get_status()
        normalized_slow_mo = max(0, int(slow_mo_ms))
        normalized_tracking = bool(tracking_enabled)
        normalized_debug_log = bool(debug_log_enabled)
        normalized_show_browser = bool(show_browser)
        debugging_enabled = normalized_tracking or normalized_debug_log

        with self._lock:
            self._refresh_locked()
            if self._process is not None or self._state.status in {"running", "stopping"}:
                payload = self._state.to_dict()
                payload["output_json_path"] = str(self._output_json_path)
                payload["trace_file_path"] = str(self._trace_file_path)
                payload["is_running"] = self._state.status in {"running", "stopping"}
                payload["can_stop"] = self._state.status in {"running", "stopping"}
                return False, "run already in progress", payload

            self._output_json_path.parent.mkdir(parents=True, exist_ok=True)
            self._trace_file_path.parent.mkdir(parents=True, exist_ok=True)

            run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
            command = [
                self._python_executable,
                "-m",
                "app.entrypoints.cli",
                "--query",
                normalized_query,
                "--max-posts",
                str(normalized_max_posts),
                "--output-json",
                str(self._output_json_path),
            ]
            if debugging_enabled:
                command.append("--debugging")
            env = os.environ.copy()
            env["DEBUG_TRACE_FILE"] = str(self._trace_file_path)
            env["HEADLESS"] = "false" if normalized_show_browser else "true"
            env["FB_STEP_DEBUG_ENABLED"] = "true" if normalized_tracking else "false"
            env["FB_SLOW_MO_MS"] = str(normalized_slow_mo if (normalized_show_browser or normalized_tracking) else 0)

            process = subprocess.Popen(  # noqa: S603
                command,
                cwd=str(self._root_dir),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._process = process
            self._stop_requested = False
            self._state = ManagedRunState(
                status="running",
                run_id=run_id,
                query=normalized_query,
                max_posts=normalized_max_posts,
                tracking_enabled=normalized_tracking,
                debug_log_enabled=normalized_debug_log,
                show_browser=normalized_show_browser,
                started_at=_utc_now_iso(),
            )

            watcher = threading.Thread(
                target=self._wait_for_process,
                args=(process, run_id),
                name=f"ui-run-watcher-{run_id}",
                daemon=True,
            )
            watcher.start()

            payload = self._state.to_dict()
            payload["output_json_path"] = str(self._output_json_path)
            payload["trace_file_path"] = str(self._trace_file_path)
            payload["is_running"] = True
            payload["can_stop"] = True
            return True, "run started", payload

    def stop_run(self) -> Tuple[bool, str, Dict[str, object]]:
        with self._lock:
            self._refresh_locked()
            process = self._process
            if process is None or self._state.status not in {"running", "stopping"}:
                payload = self._state.to_dict()
                payload["output_json_path"] = str(self._output_json_path)
                payload["trace_file_path"] = str(self._trace_file_path)
                payload["is_running"] = False
                payload["can_stop"] = False
                return False, "no running process to stop", payload

            self._stop_requested = True
            self._state.status = "stopping"
            self._state.stop_reason = "user_requested_stop"

            try:
                process.terminate()
            except OSError as exc:
                self._state.status = "failed"
                self._state.error = f"failed to stop process: {exc}"
                self._stop_requested = False
                payload = self._state.to_dict()
                payload["output_json_path"] = str(self._output_json_path)
                payload["trace_file_path"] = str(self._trace_file_path)
                payload["is_running"] = False
                payload["can_stop"] = False
                return False, "failed to stop process", payload

            payload = self._state.to_dict()
            payload["output_json_path"] = str(self._output_json_path)
            payload["trace_file_path"] = str(self._trace_file_path)
            payload["is_running"] = True
            payload["can_stop"] = True
            return True, "stop requested", payload

    def _refresh_locked(self) -> None:
        if self._process is None:
            return
        exit_code = self._process.poll()
        if exit_code is None:
            return
        self._finalize_locked(exit_code=exit_code)

    def _wait_for_process(self, process: subprocess.Popen[object], run_id: str) -> None:
        exit_code = process.wait()
        with self._lock:
            if self._state.run_id != run_id:
                return
            if self._process is process:
                self._finalize_locked(exit_code=exit_code)

    def _finalize_locked(self, *, exit_code: int) -> None:
        self._process = None
        self._state.exit_code = int(exit_code)
        self._state.finished_at = _utc_now_iso()
        if self._stop_requested:
            self._state.status = "stopped"
            self._state.error = ""
            if not self._state.stop_reason:
                self._state.stop_reason = "user_requested_stop"
            self._stop_requested = False
            return
        if exit_code == 0:
            self._state.status = "completed"
            self._state.error = ""
            self._stop_requested = False
            return
        self._state.status = "failed"
        self._state.error = f"pipeline exited with code {exit_code}"
        self._stop_requested = False
