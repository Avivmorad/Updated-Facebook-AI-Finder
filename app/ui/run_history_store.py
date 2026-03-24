import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.models.pipeline_models import PipelineResult
from app.utils.logger import get_logger
from config.presentation_config import RunHistoryConfig


logger = get_logger(__name__)


class RunHistoryStore:
    def __init__(self, config: Optional[RunHistoryConfig] = None) -> None:
        self._config = config or RunHistoryConfig()
        self._history_path = Path(self._config.history_file_path)

    def save_run(self, result: PipelineResult) -> str:
        run_id = self._build_run_id(result)
        payload = self._load_history_payload()

        payload.setdefault("schema_version", 1)
        runs = payload.setdefault("runs", [])

        runs.append(
            {
                "run_id": run_id,
                "saved_at": _utc_now_iso(),
                "run_state": result.run_state.to_dict(),
                "request_payload": result.request_payload,
                "presented_results": result.presented_results,
                "ranked_posts": result.ranked_posts,
            }
        )

        max_items = max(1, self._config.max_saved_runs)
        payload["runs"] = runs[-max_items:]

        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return run_id

    def load_runs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        payload = self._load_history_payload()
        runs = payload.get("runs", [])
        if not isinstance(runs, list):
            return []

        sorted_runs = sorted(
            runs,
            key=lambda item: str(item.get("saved_at", "")),
            reverse=True,
        )

        if limit is not None and limit >= 0:
            return sorted_runs[:limit]
        return sorted_runs

    def load_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        payload = self._load_history_payload()
        runs = payload.get("runs", [])
        if not isinstance(runs, list):
            return None

        for item in runs:
            if str(item.get("run_id")) == run_id:
                return item
        return None

    def _load_history_payload(self) -> Dict[str, Any]:
        if not self._history_path.exists():
            return {"schema_version": 1, "runs": []}

        try:
            raw = self._history_path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            logger.warning("Run history unreadable. Resetting history file payload.")
            return {"schema_version": 1, "runs": []}

        if not isinstance(parsed, dict):
            return {"schema_version": 1, "runs": []}

        runs = parsed.get("runs", [])
        if not isinstance(runs, list):
            parsed["runs"] = []

        return parsed

    def _build_run_id(self, result: PipelineResult) -> str:
        started_at = result.run_state.runtime.started_at or _utc_now_iso()
        compact_ts = started_at.replace("-", "").replace(":", "").replace(".", "").replace("+", "")
        return f"run_{compact_ts}_{uuid4().hex[:8]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
