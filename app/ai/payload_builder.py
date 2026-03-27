from typing import Any, Dict, List

from app.domain.ai import AIRequestPayload
from app.domain.input import UserQuery


def build_ai_request_payload(post_data: Dict[str, Any], user_query: UserQuery) -> AIRequestPayload:
    image_urls = _ensure_list(post_data.get("images", []))
    return AIRequestPayload(
        query=user_query.query,
        post_text=_as_text(post_data.get("post_text", "")),
        image_urls=image_urls,
        publish_date_text=_as_text(
            post_data.get("publish_date_normalized") or post_data.get("publish_date") or post_data.get("publish_date_raw", "")
        ),
        publish_date_raw=_as_text(post_data.get("publish_date_raw", "")),
        extraction_quality=_as_text(post_data.get("extraction_quality", "")),
        image_count=_as_int(post_data.get("image_count"), default=len(image_urls)),
        parser_time_reason=_as_text(post_data.get("parser_time_reason", "")),
        post_screenshot_path=_as_text(post_data.get("post_screenshot_path", "")),
    )


def _as_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _ensure_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
