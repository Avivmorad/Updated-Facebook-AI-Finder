from typing import Any, Dict, List, Optional

from config.presentation_config import PresentationConfig


class ResultPresenter:
    def __init__(self, config: Optional[PresentationConfig] = None) -> None:
        self._config = config or PresentationConfig()

    def present(self, ranked_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        list_items: List[Dict[str, Any]] = []
        detail_items: List[Dict[str, Any]] = []

        for rank, item in enumerate(ranked_posts, start=1):
            result_id = self._build_result_id(item=item, rank=rank)

            list_items.append(self._build_list_item(item=item, rank=rank, result_id=result_id))
            detail_items.append(self._build_detail_item(item=item, rank=rank, result_id=result_id))

        return {
            "total_results": len(ranked_posts),
            "results_list": list_items,
            "result_details": detail_items,
            "top_results": list_items[:5],
        }

    def _build_list_item(self, item: Dict[str, Any], rank: int, result_id: str) -> Dict[str, Any]:
        post = _to_dict(item.get("post"))
        normalized = _to_dict(post.get("normalized_post_data"))
        raw = _to_dict(post.get("raw_post_data"))
        scoring = _to_dict(item.get("scoring"))
        logic = _to_dict(item.get("logic_analysis"))

        short_recommendation = _short_text(
            str(scoring.get("recommendation_text", "")),
            max_length=self._config.recommendation_preview_max_length,
        )

        warning_flags = _collect_warning_flags(logic=logic, ai=_to_dict(item.get("ai_analysis")))
        extraction_warnings = _safe_list(post.get("extraction_warnings"))
        if post.get("extraction_error"):
            extraction_warnings.append(f"extraction_error:{post.get('extraction_error')}")
        warning_flags = _merge_warning_lists(warning_flags, extraction_warnings)

        return {
            "result_id": result_id,
            "rank": rank,
            "title": _first_non_empty(normalized.get("title"), raw.get("title"), ""),
            "price": normalized.get("price", raw.get("price")),
            "location": _first_non_empty(normalized.get("location"), raw.get("location"), ""),
            "seller_name": _first_non_empty(normalized.get("seller_name"), raw.get("seller_name"), ""),
            "publish_time": _first_non_empty(normalized.get("publish_time"), raw.get("publish_time"), ""),
            "final_score": _to_float(scoring.get("final_score"), default=0.0),
            "recommendation_code": str(scoring.get("recommendation_code", "")),
            "short_recommendation": short_recommendation,
            "warning_flags": warning_flags,
            "extraction_success": bool(post.get("extraction_success", True)),
        }

    def _build_detail_item(self, item: Dict[str, Any], rank: int, result_id: str) -> Dict[str, Any]:
        post = _to_dict(item.get("post"))
        normalized = _to_dict(post.get("normalized_post_data"))
        raw = _to_dict(post.get("raw_post_data"))
        logic = _to_dict(item.get("logic_analysis"))
        ai = _to_dict(item.get("ai_analysis"))
        scoring = _to_dict(item.get("scoring"))

        comments = _safe_list(normalized.get("comments") or raw.get("comments"))

        return {
            "result_id": result_id,
            "rank": rank,
            "post": {
                "collected_post_data": post,
                "raw_post_data": raw,
                "normalized_post_data": normalized,
            },
            "comments": {
                "count": len(comments),
                "items": comments,
            },
            "logic_analysis": logic,
            "ai_analysis": ai,
            "score_breakdown": {
                "final_score": _to_float(scoring.get("final_score"), default=0.0),
                "categories": _to_dict(scoring.get("categories")),
                "penalties": _to_dict(scoring.get("penalties")),
                "explanations": _safe_list(scoring.get("explanations")),
            },
            "recommendation": {
                "code": str(scoring.get("recommendation_code", "")),
                "text": str(scoring.get("recommendation_text", "")),
            },
            "warning_flags": _merge_warning_lists(
                _collect_warning_flags(logic=logic, ai=ai),
                _extract_post_warnings(post),
            ),
            "extraction": {
                "success": bool(post.get("extraction_success", True)),
                "error": post.get("extraction_error"),
                "warnings": _safe_list(post.get("extraction_warnings")),
            },
        }

    def _build_result_id(self, item: Dict[str, Any], rank: int) -> str:
        post = _to_dict(item.get("post"))
        normalized = _to_dict(post.get("normalized_post_data"))
        raw = _to_dict(post.get("raw_post_data"))

        candidate = _first_non_empty(
            normalized.get("post_url"),
            raw.get("post_url"),
            normalized.get("id"),
            raw.get("id"),
            "",
        )
        if candidate:
            return str(candidate)
        return f"result_{rank}"


def _to_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value).strip() if value is not None else ""
        if text:
            return text
    return ""


def _short_text(value: str, max_length: int) -> str:
    clean = value.strip()
    if len(clean) <= max_length:
        return clean
    return clean[: max(0, max_length - 3)].rstrip() + "..."


def _collect_warning_flags(logic: Dict[str, Any], ai: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []

    logic_warnings = logic.get("warning_flags")
    if isinstance(logic_warnings, list):
        for item in logic_warnings:
            text = str(item).strip()
            if text:
                warnings.append(text)

    ai_warnings = ai.get("warning_signs")
    if isinstance(ai_warnings, list):
        for item in ai_warnings:
            text = str(item).strip()
            if text:
                warnings.append(f"ai:{text}")

    # Preserve order and avoid duplicates while keeping all warning signs visible.
    seen = set()
    output: List[str] = []
    for item in warnings:
        if item not in seen:
            output.append(item)
            seen.add(item)
    return output


def _extract_post_warnings(post: Dict[str, Any]) -> List[str]:
    warnings = _safe_list(post.get("extraction_warnings"))
    error = post.get("extraction_error")
    if error:
        warnings.append(f"extraction_error:{error}")
    if not bool(post.get("extraction_success", True)):
        warnings.append("extraction_failed")
    return warnings


def _merge_warning_lists(primary: List[str], secondary: List[str]) -> List[str]:
    output: List[str] = []
    seen = set()
    for item in primary + secondary:
        text = str(item).strip()
        if text and text not in seen:
            output.append(text)
            seen.add(text)
    return output
