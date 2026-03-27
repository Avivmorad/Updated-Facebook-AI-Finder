from typing import Any, Dict, List, Optional

from app.config.presentation import PresentationConfig


class ResultPresenter:
    def __init__(self, config: Optional[PresentationConfig] = None) -> None:
        self._config = config or PresentationConfig()

    def present(self, ranked_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        list_items: List[Dict[str, Any]] = []
        detail_items: List[Dict[str, Any]] = []

        for item in ranked_posts:
            rank = int(item.get("rank", len(list_items) + 1))
            result_id = self._build_result_id(item=item, rank=rank)
            list_items.append(self._build_list_item(item, rank, result_id))
            detail_items.append(self._build_detail_item(item, rank, result_id))

        return {
            "total_results": len(ranked_posts),
            "results_list": list_items,
            "result_details": detail_items,
            "top_results": list_items[:5],
        }

    def _build_list_item(self, item: Dict[str, Any], rank: int, result_id: str) -> Dict[str, Any]:
        post = _to_dict(item.get("post"))
        ai_match = _to_dict(item.get("ai_match"))

        short_summary = _short_text(
            str(ai_match.get("match_reason") or ai_match.get("detected_item") or "").strip(),
            self._config.summary_preview_max_length,
        )

        return {
            "result_id": result_id,
            "rank": rank,
            "post_link": str(post.get("post_link", "")),
            "match_score": _to_float(item.get("match_score"), default=0.0),
            "short_summary": short_summary,
            "publish_time": str(post.get("publish_date_normalized") or post.get("publish_date_raw") or post.get("publish_date", "")),
            "extraction_status": str(post.get("extraction_quality", "")),
            "detected_item": str(ai_match.get("detected_item", "")),
            "confidence": _to_float(ai_match.get("confidence"), default=0.0),
            "match_reason": str(ai_match.get("match_reason", "")),
        }

    def _build_detail_item(self, item: Dict[str, Any], rank: int, result_id: str) -> Dict[str, Any]:
        post = _to_dict(item.get("post"))
        ai_match = _to_dict(item.get("ai_match"))
        return {
            "result_id": result_id,
            "rank": rank,
            "extracted_data": post,
            "ai_analysis": ai_match,
            "match_explanation": str(ai_match.get("match_reason", "")),
        }

    def _build_result_id(self, item: Dict[str, Any], rank: int) -> str:
        post = _to_dict(item.get("post"))
        candidate = str(post.get("post_link", "")).strip()
        return candidate or f"result_{rank}"


def _to_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _short_text(value: str, max_length: int) -> str:
    clean = value.strip()
    if len(clean) <= max_length:
        return clean
    return clean[: max(0, max_length - 3)].rstrip() + "..."
