from typing import Any, Dict, List

from app.domain.posts import CollectedPost


def normalize_post_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    collected = CollectedPost(
        post_link=_clean_text(raw_data.get("post_link")),
        post_text=_clean_text(raw_data.get("post_text")),
        images=_clean_string_list(raw_data.get("images", [])),
        publish_date=_clean_text(raw_data.get("publish_date")),
    )
    return collected.to_dict()


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_string_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []

    output: List[str] = []
    seen = set()
    for item in values:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)

    return output
