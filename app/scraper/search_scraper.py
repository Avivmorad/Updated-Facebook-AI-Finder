from typing import Any, Dict, List

from app.models.input_models import SearchRequest
from app.scraper.post_extractor import PostExtractor
from app.scraper.platform_search_executor import PlatformSearchExecutor
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class SearchScraper:
    def __init__(self) -> None:
        self._executor = PlatformSearchExecutor()
        self._post_extractor = PostExtractor()

    def search_posts(self, request: SearchRequest, max_posts: int) -> List[Dict[str, Any]]:
        log_event(logger, 20, "search_started", query=request.query_text, max_posts=max_posts)
        execution = self._executor.execute_search(
            query_text=request.query_text,
            max_posts=max_posts,
        )

        for warning in execution.warnings:
            logger.warning("Search warning: %s", warning)

        if execution.fatal_error:
            logger.error("Search fatal error: %s", execution.fatal_error)

        if execution.items:
            items = [item.to_dict() for item in execution.items][:max_posts]
            log_event(
                logger,
                20,
                "search_finished",
                found=len(items),
                attempts=execution.attempts,
                warnings=len(execution.warnings),
            )
            return items

        # Graceful fallback for partial system availability.
        log_event(
            logger,
            30,
            "search_fallback_used",
            attempts=execution.attempts,
            fatal_error=execution.fatal_error,
        )
        return self._fallback_results(request=request, max_posts=max_posts)

    def open_post(self, post_summary: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "post_id": post_summary.get("post_id", ""),
            "title": post_summary.get("title", ""),
            "region": post_summary.get("region", ""),
            "url": post_summary.get("url", ""),
            "snippet": post_summary.get("snippet", ""),
            "price_text": post_summary.get("price_text"),
            "source_platform": post_summary.get("source_platform", "facebook_marketplace"),
            "raw_reference": post_summary.get("raw", {}),
        }

    def collect_post_data(self, opened_post: Dict[str, Any]) -> Dict[str, Any]:
        extraction = self._post_extractor.extract_post(opened_post)
        normalized = extraction.normalized_post_data

        return {
            **opened_post,
            "raw_post_data": extraction.raw_post_data,
            "normalized_post_data": normalized,
            "description": normalized.get("text", opened_post.get("snippet", "")),
            "price": normalized.get("price") if normalized.get("price") is not None else 0.0,
            "has_image": bool(normalized.get("has_image", False)),
            "title": normalized.get("title") or opened_post.get("title", ""),
            "region": normalized.get("location") or opened_post.get("region", ""),
            "publish_age": normalized.get("publish_age"),
            "post_url": normalized.get("url") or opened_post.get("url", ""),
            "images": normalized.get("images", []),
            "seller_name": normalized.get("seller_name"),
            "comments": normalized.get("comments", []),
            "important_visible_signals": normalized.get("important_visible_signals", []),
            "extraction_warnings": extraction.warnings,
            "extraction_error": extraction.error,
            "extraction_success": extraction.success,
            "seller_rating": 4.5,
        }

    def _fallback_results(self, request: SearchRequest, max_posts: int) -> List[Dict[str, Any]]:
        count = min(max_posts, 3)
        return [
            {
                "post_id": f"fallback-{index + 1}",
                "title": f"{request.query_text} fallback #{index + 1}",
                "url": "",
                "snippet": request.query_text,
                "price_text": None,
                "region": request.target_regions[0] if request.target_regions else "all-country",
                "source_platform": "facebook_marketplace",
                "raw": {"fallback": True},
                "fallback_reason": "search_execution_empty_or_failed",
            }
            for index in range(count)
        ]
