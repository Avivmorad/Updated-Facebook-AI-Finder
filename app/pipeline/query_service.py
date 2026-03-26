from typing import Any, Dict, List, Optional, Tuple

from app.domain.input import UserQuery, ValidationErrorItem


class QueryValidationError(ValueError):
    def __init__(self, errors: List[ValidationErrorItem]) -> None:
        self.errors = errors
        super().__init__("query_validation_failed")

    def to_dict(self) -> Dict[str, Any]:
        return {"errors": [item.to_dict() for item in self.errors]}


def validate_raw_query_input(raw_input: Dict[str, Any]) -> UserQuery:
    errors: List[ValidationErrorItem] = []
    candidate = raw_input.get("query")
    if candidate is None:
        candidate = raw_input.get("main_text")

    if candidate is None:
        errors.append(ValidationErrorItem(field="query", message="is required"))
    elif not isinstance(candidate, str):
        errors.append(ValidationErrorItem(field="query", message="must be a string"))

    query = str(candidate).strip() if isinstance(candidate, str) else ""
    if candidate is not None and isinstance(candidate, str) and not query:
        errors.append(ValidationErrorItem(field="query", message="must be a non-empty string"))

    if errors:
        raise QueryValidationError(errors)

    return UserQuery(query=query)


class QueryService:
    def build_user_query(self, raw_user_input: Dict[str, object]) -> UserQuery:
        validated = validate_raw_query_input(raw_user_input)
        return UserQuery(query=validated.query.strip())

    def validate_and_build(
        self,
        raw_user_input: Dict[str, object],
    ) -> Tuple[Optional[UserQuery], List[Dict[str, str]]]:
        try:
            query = self.build_user_query(raw_user_input)
            return query, []
        except QueryValidationError as exc:
            return None, [item for item in exc.to_dict()["errors"]]
