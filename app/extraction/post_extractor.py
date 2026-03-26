from typing import Any, Dict, List, Optional, Set

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.browser.facebook_access_adapter import FacebookAccessAdapter, FacebookAuthenticationRequiredError
from app.config.browser import BrowserConfig
from app.domain.posts import PostExtractionResult
from app.extraction.post_normalizer import normalize_post_data
from app.utils.debugging import debug_info, debug_warning
from app.utils.logger import get_logger


logger = get_logger(__name__)


class PostExtractor:
    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self._config = config or BrowserConfig()
        self._facebook_access = FacebookAccessAdapter(self._config)

    def extract_post(self, reference: Dict[str, Any]) -> PostExtractionResult:
        post_link = str(reference.get("post_link") or reference.get("url") or "").strip()
        post_id = str(reference.get("post_id") or "").strip()
        result = PostExtractionResult(reference={"post_id": post_id, "post_link": post_link})

        if not post_link:
            result.success = False
            result.error = "missing_post_link"
            result.warnings.append("Cannot open post without post_link")
            return result

        attempts = max(1, self._config.retries + 1)
        last_error = "post_extraction_failed"
        debug_info("Opening the post page to extract its text, images, and publish date.")

        for attempt in range(1, attempts + 1):
            try:
                with self._facebook_access.authenticated_session() as session:
                    page = session.page
                    self._open_post_page(page, post_link)
                    raw = self._extract_raw_post(page, post_link)
                    result.raw_post_data = raw
                    result.normalized_post_data = normalize_post_data(raw)
                    if attempt > 1:
                        result.warnings.append(f"post_extraction_retry_success:{attempt}")
                    debug_info(
                        f"Extraction succeeded. Text={'yes' if result.normalized_post_data.get('post_text') else 'no'}, "
                        f"images={len(result.normalized_post_data.get('images', []))}, "
                        f"publish_date={'yes' if result.normalized_post_data.get('publish_date') else 'no'}."
                    )
                    return result
            except FacebookAuthenticationRequiredError as exc:
                last_error = str(exc)
                result.warnings.append("facebook_authentication_required")
                debug_warning("The saved Chrome profile is not logged in to Facebook, so extraction cannot continue.")
                break
            except (PlaywrightTimeoutError, PlaywrightError, RuntimeError) as exc:
                last_error = str(exc)
                result.warnings.append(f"extraction_attempt_{attempt}_failed")
                logger.warning("Post extraction attempt %s/%s failed for %s: %s", attempt, attempts, post_link, last_error)
                debug_warning(f"Post extraction attempt {attempt}/{attempts} failed. I will retry if possible.")

        result.success = False
        result.error = last_error
        debug_warning(f"I could not extract this post. Reason: {last_error}")
        return result

    def _open_post_page(self, page: Page, post_link: str) -> None:
        response = page.goto(post_link, wait_until="commit", timeout=self._config.timeout_ms)
        if response is not None and not response.ok:
            raise RuntimeError(f"post page load failed with status {response.status}")
        if str(getattr(page, "url", "") or "").strip() == "about:blank":
            raise RuntimeError(f"post page navigation ended on about:blank for {post_link}")

        page.wait_for_timeout(1500)
        for selector in self._config.selectors_post_ready:
            try:
                page.wait_for_selector(selector, timeout=self._config.timeout_ms)
                break
            except PlaywrightTimeoutError:
                continue

    def _extract_raw_post(self, page: Page, post_link: str) -> Dict[str, Any]:
        return {
            "post_link": post_link,
            "post_text": self._first_text(page, self._config.selectors_post_text),
            "publish_date": self._first_text(page, self._config.selectors_post_publish),
            "images": self._extract_images(page),
        }

    def _first_text(self, page: Page, selectors: List[str]) -> str:
        for selector in selectors:
            try:
                node = page.query_selector(selector)
            except PlaywrightError:
                continue
            if node is None:
                continue
            try:
                text = (node.inner_text() or "").strip()
            except PlaywrightError:
                continue
            if text:
                return text
        return ""

    def _extract_images(self, page: Page) -> List[str]:
        urls: List[str] = []
        seen: Set[str] = set()

        for selector in self._config.selectors_post_images:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue

            for node in nodes:
                try:
                    src = (node.get_attribute("src") or "").strip()
                except PlaywrightError:
                    continue
                if not src or src in seen:
                    continue
                seen.add(src)
                urls.append(src)

        return urls
