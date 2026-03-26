import json
from typing import Any, Dict, List, Tuple

from app.domain.ai import AIMatchResult
from app.utils.logger import get_logger


logger = get_logger(__name__)


def parse_ai_response(raw_text: str) -> Tuple[AIMatchResult | None, List[str], Dict[str, Any]]:
    if not raw_text.strip():
        return None, ["empty_ai_response"], {}

    try:
        parsed_json = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse AI JSON response: %s", str(exc))
        return None, [f"invalid_json:{str(exc)}"], {}

    if not isinstance(parsed_json, dict):
        return None, ["ai_response_not_object"], {}

    validation_errors = _validate_schema(parsed_json)
    if validation_errors:
        return None, validation_errors, parsed_json

    result = AIMatchResult(
        is_relevant=bool(parsed_json["is_relevant"]),
        match_score=_clamp_score(parsed_json["match_score"]),
        detected_item=str(parsed_json["detected_item"]).strip(),
        match_reason=str(parsed_json["match_reason"]).strip(),
        confidence=_clamp_score(parsed_json["confidence"]),
    )
    return result, [], parsed_json


def _validate_schema(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    required_keys = {
        "is_relevant",
        "match_score",
        "detected_item",
        "match_reason",
        "confidence",
    }

    for key in sorted(required_keys):
        if key not in data:
            errors.append(f"missing_required_field:{key}")

    extra_keys = sorted(set(data.keys()) - required_keys)
    for key in extra_keys:
        errors.append(f"unexpected_field:{key}")

    if "is_relevant" in data and not isinstance(data.get("is_relevant"), bool):
        errors.append("invalid_type:is_relevant:expected_boolean")

    for key in ["detected_item", "match_reason"]:
        if key in data and not isinstance(data.get(key), str):
            errors.append(f"invalid_type:{key}:expected_string")

    for key in ["match_score", "confidence"]:
        if key in data and not isinstance(data.get(key), (int, float)):
            errors.append(f"invalid_type:{key}:expected_number")

    return errors


def _clamp_score(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(100.0, round(numeric, 2)))
