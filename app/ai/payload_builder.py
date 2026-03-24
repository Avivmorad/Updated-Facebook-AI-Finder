from typing import Any, Dict, List

from app.models.ai_models import AIRequestPayload
from app.models.input_models import SearchRequest


def build_ai_request_payload(post_data: Dict[str, Any], request: SearchRequest) -> AIRequestPayload:
    normalized = post_data.get("normalized_post_data", {})

    comments = _ensure_list(normalized.get("comments", post_data.get("comments", [])))
    signals = _ensure_list(
        normalized.get("important_visible_signals", post_data.get("important_visible_signals", []))
    )
    images = _ensure_list(normalized.get("images", post_data.get("images", [])))

    return AIRequestPayload(
        product_query=request.query_text,
        post_title=_as_text(normalized.get("title", post_data.get("title", ""))),
        post_text=_as_text(normalized.get("text", post_data.get("description", ""))),
        price=_as_optional_float(normalized.get("price", post_data.get("price"))),
        location=_as_text(normalized.get("location", post_data.get("region", ""))),
        seller_name=_as_text(normalized.get("seller_name", post_data.get("seller_name", ""))),
        comments=comments,
        signals=signals,
        image_urls=images,
    )


def _ensure_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    output: List[str] = []
    for item in value:
        text = _as_text(item)
        if text:
            output.append(text)
    return output


def _as_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _as_optional_float(value: Any):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
