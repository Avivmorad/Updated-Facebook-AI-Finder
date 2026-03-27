import json
import re
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
        extracted_json = _extract_json_object(raw_text)
        if extracted_json is None:
            logger.warning("Failed to parse AI JSON response: %s", str(exc))
            return None, [f"invalid_json:{str(exc)}"], {}
        parsed_json = extracted_json

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
        is_recent_24h=bool(parsed_json["is_recent_24h"]),
        publish_date_observed=str(parsed_json["publish_date_observed"]).strip(),
        publish_date_reason=str(parsed_json["publish_date_reason"]).strip(),
        publish_date_confidence=_clamp_score(parsed_json["publish_date_confidence"]),
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
        "is_recent_24h",
        "publish_date_observed",
        "publish_date_reason",
        "publish_date_confidence",
    }

    for key in sorted(required_keys):
        if key not in data:
            errors.append(f"missing_required_field:{key}")

    extra_keys = sorted(set(data.keys()) - required_keys)
    for key in extra_keys:
        errors.append(f"unexpected_field:{key}")

    if "is_relevant" in data and not isinstance(data.get("is_relevant"), bool):
        errors.append("invalid_type:is_relevant:expected_boolean")
    if "is_recent_24h" in data and not isinstance(data.get("is_recent_24h"), bool):
        errors.append("invalid_type:is_recent_24h:expected_boolean")

    for key in ["detected_item", "match_reason", "publish_date_observed", "publish_date_reason"]:
        if key in data and not isinstance(data.get(key), str):
            errors.append(f"invalid_type:{key}:expected_string")

    for key in ["match_score", "confidence", "publish_date_confidence"]:
        if key in data and not isinstance(data.get(key), (int, float)):
            errors.append(f"invalid_type:{key}:expected_number")

    return errors


def _clamp_score(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(100.0, round(numeric, 2)))


def _extract_json_object(raw_text: str) -> Dict[str, Any] | None:
    text = str(raw_text or "").strip()
    if not text:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
