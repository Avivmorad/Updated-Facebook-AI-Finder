from typing import Any, Dict, List

from app.browser.groups_feed_scanner import GroupsFeedScanner
from app.domain.input import UserQuery
from app.extraction.post_extractor import PostExtractor
from app.utils.app_errors import make_app_error
from app.utils.debugging import debug_app_error, debug_info, debug_warning
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
            debug_warning("DBG_SEARCH_WARNING", f"Scan warning: {warning}")

        if execution.fatal_error:
            logger.error("Search fatal error: %s", execution.fatal_error)
            app_error = make_app_error(
                code=str(execution.fatal_error).strip() or "ERR_GROUPS_SCAN_FAILED",
                technical_details=f"fatal_error={execution.fatal_error}",
            )
            debug_app_error(app_error)
            raise app_error

        items = [item.to_dict() for item in execution.items][:max_posts]
        log_event(logger, 20, "search_finished", found=len(items), attempts=execution.attempts)
        debug_info("DBG_SEARCH_DONE", f"Feed scan completed after {execution.attempts} attempt(s).")
        return items

    def open_post(self, post_summary: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "post_id": post_summary.get("post_id", ""),
            "post_link": post_summary.get("post_link", ""),
            "preview_text": post_summary.get("preview_text", ""),
            "raw_reference": post_summary.get("raw", {}),
        }

    def collect_posts_from_links(self, post_links: List[str]) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        for link in post_links:
            normalized_link = str(link).strip()
            if not normalized_link:
                continue
            opened = self.open_post({"post_id": "", "post_link": normalized_link, "preview_text": "", "raw": {}})
            collected.append(self.collect_post_data(opened))
        return collected

    def collect_post_data(self, opened_post: Dict[str, Any]) -> Dict[str, Any]:
        extraction = self._post_extractor.extract_post(opened_post)
        normalized = dict(extraction.normalized_post_data)
        raw_screenshot_path = str(extraction.raw_post_data.get("post_screenshot_path") or "").strip()
        normalized_screenshot_path = str(normalized.get("post_screenshot_path") or "").strip()
        post_screenshot_path = normalized_screenshot_path or raw_screenshot_path

        publish_date_raw = str(normalized.get("publish_date_raw") or extraction.raw_post_data.get("publish_date_raw") or "").strip()
        publish_date_normalized = (
            str(normalized.get("publish_date_normalized") or extraction.raw_post_data.get("publish_date_normalized") or "").strip()
        )

        return {
            "post_id": normalized.get("post_id") or opened_post.get("post_id", ""),
            "post_link": normalized.get("post_link") or opened_post.get("post_link", ""),
            "post_text": normalized.get("post_text", ""),
            "images": normalized.get("images", []),
            "image_count": int(normalized.get("image_count") or len(normalized.get("images", []))),
            "publish_date_raw": publish_date_raw,
            "publish_date_normalized": publish_date_normalized,
            "publish_date": publish_date_normalized or publish_date_raw,
            "extraction_quality": str(normalized.get("extraction_quality") or "failed"),
            "post_screenshot_path": post_screenshot_path,
            "screenshot_paths": normalized.get("screenshot_paths", []),
            "raw_post_data": extraction.raw_post_data,
            "normalized_post_data": normalized,
            "extraction_warnings": extraction.warnings,
            "extraction_error": extraction.error,
            "extraction_success": extraction.success,
        }
