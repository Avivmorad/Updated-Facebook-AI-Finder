import json
from typing import Any, Dict, List, Tuple

from app.models.ai_models import AIParsedAnalysis
from app.utils.logger import get_logger


logger = get_logger(__name__)


def parse_ai_response(raw_text: str) -> Tuple[AIParsedAnalysis | None, List[str], Dict[str, Any]]:
    errors: List[str] = []

    if not raw_text.strip():
        return None, ["empty_ai_response"], {}

    parsed_obj: Dict[str, Any]
    try:
        parsed_json = json.loads(raw_text)
        if not isinstance(parsed_json, dict):
            return None, ["ai_response_not_object"], {}
        parsed_obj = parsed_json
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse AI JSON response: %s", str(exc))
        return None, [f"invalid_json: {str(exc)}"], {}

    validation_errors = _validate_schema(parsed_obj)
    if validation_errors:
        return None, validation_errors, parsed_obj

    relevance_score = _clamp_float(parsed_obj.get("relevance_score"), 0.0, 1.0)

    result = AIParsedAnalysis(
        post_meaning=str(parsed_obj.get("post_meaning", "")).strip(),
        seller_intent=str(parsed_obj.get("seller_intent", "")).strip(),
        reliability_signals=_to_str_list(parsed_obj.get("reliability_signals", [])),
        pros=_to_str_list(parsed_obj.get("pros", [])),
        cons=_to_str_list(parsed_obj.get("cons", [])),
        warning_signs=_to_str_list(parsed_obj.get("warning_signs", [])),
        recommendation=str(parsed_obj.get("recommendation", "consider")).strip(),
        image_product_match=str(parsed_obj.get("image_product_match", "unclear")).strip(),
        logic_notes=str(parsed_obj.get("logic_notes", "")).strip(),
        relevance_score=relevance_score,
    )

    return result, [], parsed_obj


def _validate_schema(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    required_keys = {
        "post_meaning",
        "seller_intent",
        "reliability_signals",
        "pros",
        "cons",
        "warning_signs",
        "recommendation",
        "image_product_match",
        "logic_notes",
        "relevance_score",
    }

    for key in sorted(required_keys):
        if key not in data:
            errors.append(f"missing_required_field:{key}")

    for key in ["reliability_signals", "pros", "cons", "warning_signs"]:
        if key in data and not isinstance(data.get(key), list):
            errors.append(f"invalid_type:{key}:expected_list")

    for key in ["post_meaning", "seller_intent", "recommendation", "image_product_match", "logic_notes"]:
        if key in data and not isinstance(data.get(key), str):
            errors.append(f"invalid_type:{key}:expected_string")

    if "relevance_score" in data and not isinstance(data.get("relevance_score"), (int, float)):
        errors.append("invalid_type:relevance_score:expected_number")

    recommendation = str(data.get("recommendation", ""))
    if recommendation and recommendation not in {"buy", "consider", "skip"}:
        errors.append("invalid_value:recommendation")

    image_match = str(data.get("image_product_match", ""))
    if image_match and image_match not in {"match", "mismatch", "unclear"}:
        errors.append("invalid_value:image_product_match")

    return errors


def _to_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    output: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            output.append(text)
    return output


def _clamp_float(value: Any, min_v: float, max_v: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.5
    return max(min_v, min(max_v, numeric))
