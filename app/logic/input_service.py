from typing import Any, Dict, List, Optional, Tuple

from app.logic.input_normalization import normalize_to_search_request
from app.logic.input_validation import InputValidationError, validate_raw_search_input
from app.logic.saved_searches import SavedSearchStore
from app.models.input_models import SavedSearch, SearchRequest


class InputService:
    def __init__(self, saved_search_store: Optional[SavedSearchStore] = None) -> None:
        self._saved_search_store = saved_search_store or SavedSearchStore()

    def build_search_request(self, raw_user_input: Dict[str, Any]) -> SearchRequest:
        validated = validate_raw_search_input(raw_user_input)
        return normalize_to_search_request(validated)

    def validate_and_build(
        self, raw_user_input: Dict[str, Any]
    ) -> Tuple[Optional[SearchRequest], List[Dict[str, str]]]:
        try:
            request = self.build_search_request(raw_user_input)
            return request, []
        except InputValidationError as exc:
            return None, [item for item in exc.to_dict()["errors"]]

    def save_search(self, search_name: str, raw_user_input: Dict[str, Any]) -> SavedSearch:
        validated = validate_raw_search_input(raw_user_input)
        return self._saved_search_store.save_search(search_name=search_name, search_input=validated)

    def load_previous_searches(self) -> List[SavedSearch]:
        return self._saved_search_store.load_previous_searches()
