import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.models.input_models import RawSearchInput, SavedSearch
from app.utils.logger import get_logger


logger = get_logger(__name__)


class SavedSearchStore:
    def __init__(self, file_path: str = "data/saved_searches.json") -> None:
        self._file_path = Path(file_path)
        self._ensure_storage_exists()

    def load_previous_searches(self) -> List[SavedSearch]:
        payload = self._read_json_payload()
        searches: List[SavedSearch] = []

        for item in payload:
            name = item.get("name")
            created_at = item.get("created_at")
            input_payload = item.get("input_payload")

            if not isinstance(name, str) or not isinstance(created_at, str) or not isinstance(input_payload, dict):
                logger.warning("Skipping invalid saved search record")
                continue

            searches.append(
                SavedSearch(
                    name=name,
                    created_at=created_at,
                    input_payload=input_payload,
                )
            )

        return searches

    def save_search(self, search_name: str, search_input: RawSearchInput) -> SavedSearch:
        timestamp = datetime.now(timezone.utc).isoformat()
        saved_search = SavedSearch(
            name=search_name.strip(),
            created_at=timestamp,
            input_payload=search_input.to_dict(),
        )

        payload = self._read_json_payload()
        payload.append(asdict(saved_search))
        self._write_json_payload(payload)

        return saved_search

    def _ensure_storage_exists(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("[]", encoding="utf-8")

    def _read_json_payload(self) -> List[dict]:
        self._ensure_storage_exists()

        try:
            content = self._file_path.read_text(encoding="utf-8").strip()
            if not content:
                return []
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            logger.warning("Saved searches file is not a list. Resetting in-memory payload")
            return []
        except json.JSONDecodeError:
            logger.warning("Saved searches file contains invalid JSON. Resetting in-memory payload")
            return []

    def _write_json_payload(self, payload: List[dict]) -> None:
        self._file_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
