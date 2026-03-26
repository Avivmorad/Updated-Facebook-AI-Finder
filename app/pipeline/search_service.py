from typing import Any, Dict, List

from app.browser.groups_feed_scanner import GroupsFeedScanner
from app.domain.input import UserQuery
from app.extraction.post_extractor import PostExtractor
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class SearchService:
    def __init__(self) -> None:
        self._scanner = GroupsFeedScanner()
        self._post_extractor = PostExtractor()

    def search_posts(self, user_query: UserQuery, max_posts: int) -> List[Dict[str, Any]]:
        log_event(logger, 20, "search_started", query=user_query.query, max_posts=max_posts)
        execution = self._scanner.execute_search(query_text=user_query.query, max_posts=max_posts)

        for warning in execution.warnings:
            logger.warning("Search warning: %s", warning)

        if execution.fatal_error:
            logger.error("Search fatal error: %s", execution.fatal_error)
            return []

        items = [item.to_dict() for item in execution.items][:max_posts]
        log_event(logger, 20, "search_finished", found=len(items), attempts=execution.attempts)
        return items

    def open_post(self, post_summary: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "post_id": post_summary.get("post_id", ""),
            "post_link": post_summary.get("post_link", ""),
            "preview_text": post_summary.get("preview_text", ""),
            "raw_reference": post_summary.get("raw", {}),
        }

    def collect_post_data(self, opened_post: Dict[str, Any]) -> Dict[str, Any]:
        extraction = self._post_extractor.extract_post(opened_post)
        normalized = extraction.normalized_post_data
        return {
            "post_id": opened_post.get("post_id", ""),
            "post_link": normalized.get("post_link") or opened_post.get("post_link", ""),
            "post_text": normalized.get("post_text", ""),
            "images": normalized.get("images", []),
            "publish_date": normalized.get("publish_date", ""),
            "raw_post_data": extraction.raw_post_data,
            "normalized_post_data": normalized,
            "extraction_warnings": extraction.warnings,
            "extraction_error": extraction.error,
            "extraction_success": extraction.success,
        }
