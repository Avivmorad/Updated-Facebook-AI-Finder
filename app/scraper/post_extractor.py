from typing import Any, Dict, List, Optional, Set

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.models.post_extraction_models import PostExtractionResult
from app.scraper.facebook_access_adapter import FacebookAccessAdapter, FacebookAuthenticationRequiredError
from app.scraper.post_normalizer import normalize_post_data
from app.utils.logger import get_logger, log_event
from config.platform_access_config import PlatformAccessConfig


logger = get_logger(__name__)


class PostExtractor:
    def __init__(self, config: Optional[PlatformAccessConfig] = None) -> None:
        self._config = config or PlatformAccessConfig()
        self._facebook_access = FacebookAccessAdapter(self._config)

    def extract_post(self, reference: Dict[str, Any]) -> PostExtractionResult:
        post_url = str(reference.get("url") or "").strip()
        post_id = str(reference.get("post_id") or "").strip()

        result = PostExtractionResult(reference={"post_id": post_id, "url": post_url})

        if not post_url:
            result.success = False
            result.error = "missing_post_url"
            result.warnings.append("Cannot open post without url")
            return result

        attempts = max(1, self._config.retries + 1)
        last_error = "post_extraction_failed"

        for attempt in range(1, attempts + 1):
            try:
                with self._facebook_access.authenticated_session() as session:
                    page = session.page
                    self._open_post_page(page, post_url)
                    raw = self._extract_raw_post(page=page, reference=reference)
                    normalized = normalize_post_data(raw)

                    result.raw_post_data = raw
                    result.normalized_post_data = normalized
                    if attempt > 1:
                        result.warnings.append(f"Post extraction succeeded on retry attempt {attempt}")
                    return result
            except FacebookAuthenticationRequiredError as exc:
                last_error = str(exc)
                result.warnings.append("facebook_authentication_required")
                logger.warning("Post extraction stopped because Facebook authentication is required: %s", last_error)
                break
            except (PlaywrightTimeoutError, PlaywrightError, RuntimeError) as exc:
                last_error = str(exc)
                result.warnings.append(f"extraction_attempt_{attempt}_failed")
                logger.warning(
                    "Post extraction attempt %s/%s failed for %s: %s",
                    attempt,
                    attempts,
                    post_url,
                    last_error,
                )

        result.success = False
        result.error = last_error
        result.warnings.append("Post extraction failed, returning minimal fallback data")

        raw = {
            "post_id": post_id,
            "url": post_url,
            "title_text": str(reference.get("title") or ""),
            "post_text": str(reference.get("snippet") or ""),
            "price_text": str(reference.get("price_text") or ""),
            "location_text": str(reference.get("region") or ""),
            "publish_text": "",
            "image_urls": [],
            "seller_name": "",
            "comments": [],
            "important_visible_signals": [],
            "raw_reference": dict(reference),
        }
        result.raw_post_data = raw
        result.normalized_post_data = normalize_post_data(raw)
        return result

    def _open_post_page(self, page: Page, post_url: str) -> None:
        current_url = str(getattr(page, "url", "") or "").strip()
        log_event(logger, 20, "post_navigation_requested", current_url=current_url, target_url=post_url)
        try:
            response = page.goto(post_url, wait_until="commit", timeout=self._config.timeout_ms)
        except PlaywrightTimeoutError:
            response = None

        if response is not None and not response.ok:
            raise RuntimeError(f"post page load failed with status {response.status}")

        final_url = str(getattr(page, "url", "") or "").strip()
        log_event(
            logger,
            20,
            "post_navigation_completed",
            final_url=final_url,
            http_status=response.status if response is not None else "none",
            target_url=post_url,
        )
        if final_url == "about:blank":
            raise RuntimeError(f"post page navigation ended on about:blank for {post_url}")

        page.wait_for_timeout(2000)

        for selector in self._config.selectors_post_ready:
            try:
                page.wait_for_selector(selector, timeout=self._config.timeout_ms)
                break
            except PlaywrightTimeoutError:
                continue

        try:
            page.wait_for_load_state("networkidle", timeout=min(8000, self._config.timeout_ms))
        except PlaywrightTimeoutError:
            # Some pages keep long network activity. Keep partial state.
            pass

    def _extract_raw_post(self, page: Page, reference: Dict[str, Any]) -> Dict[str, Any]:
        meta_title = self._meta_content(page, ["og:title", "twitter:title"])
        meta_description = self._meta_content(page, ["og:description", "twitter:description", "description"])
        page_title = self._page_title(page)

        title = self._first_text(page, self._config.selectors_post_title)
        if self._is_generic_title(title):
            title = meta_title or self._title_from_page_title(page_title)

        post_text = self._first_text(page, self._config.selectors_post_text) or meta_description
        price_text = self._first_text(page, self._config.selectors_post_price)
        if not price_text:
            price_text = str(reference.get("price_text") or "").strip() or None

        location_text = self._first_text(page, self._config.selectors_post_location)
        if self._is_generic_or_price_text(location_text):
            candidate_location = str(reference.get("region") or "").strip()
            location_text = candidate_location if not self._is_generic_or_price_text(candidate_location) else None

        publish_text = self._first_text(page, self._config.selectors_post_publish)
        seller_name = self._first_text(page, self._config.selectors_post_seller)

        image_urls = self._extract_images(page)
        comments = self._extract_comments(page)
        signals = self._extract_signals(page)

        return {
            "post_id": str(reference.get("post_id") or "").strip(),
            "url": str(reference.get("url") or "").strip(),
            "title_text": title,
            "post_text": post_text,
            "price_text": price_text,
            "location_text": location_text,
            "publish_text": publish_text,
            "image_urls": image_urls,
            "seller_name": seller_name,
            "comments": comments,
            "important_visible_signals": signals,
            "raw_reference": dict(reference),
        }

    def _meta_content(self, page: Page, keys: List[str]) -> Optional[str]:
        for key in keys:
            for selector in [f'meta[property="{key}"]', f'meta[name="{key}"]']:
                try:
                    node = page.query_selector(selector)
                except PlaywrightError:
                    continue
                if node is None:
                    continue
                try:
                    content = (node.get_attribute("content") or "").strip()
                except PlaywrightError:
                    continue
                if content:
                    return content
        return None

    def _page_title(self, page: Page) -> Optional[str]:
        try:
            value = page.title().strip()
        except PlaywrightError:
            return None
        return value or None

    def _title_from_page_title(self, page_title: Optional[str]) -> Optional[str]:
        if not page_title:
            return None
        return page_title.split(" - ", 1)[0].strip() or None

    def _is_generic_title(self, value: Optional[str]) -> bool:
        text = (value or "").strip().lower()
        return not text or text in {"marketplace", "facebook", "facebook marketplace"}

    def _is_generic_or_price_text(self, value: Optional[str]) -> bool:
        text = (value or "").strip().lower()
        if not text:
            return True
        if any(marker in text for marker in ["$", "₪", "€", "usd", "ils", "eur"]):
            return True
        return text in {"marketplace", "just listed", "פורסמו ממש עכשיו"}

    def _first_text(self, page: Page, selectors: List[str]) -> Optional[str]:
        for selector in selectors:
            try:
                node = page.query_selector(selector)
            except PlaywrightError:
                continue

            if node is None:
                continue

            try:
                text = node.inner_text().strip()
            except PlaywrightError:
                continue

            if text:
                return text
        return None

    def _extract_images(self, page: Page) -> List[str]:
        urls: List[str] = []
        seen: Set[str] = set()

        for node in page.query_selector_all("img"):
            try:
                src = (node.get_attribute("src") or "").strip()
            except PlaywrightError:
                continue

            if not src or src in seen:
                continue

            seen.add(src)
            urls.append(src)

        return urls

    def _extract_comments(self, page: Page) -> List[str]:
        comments: List[str] = []
        seen: Set[str] = set()

        for selector in self._config.selectors_post_comments:
            nodes = page.query_selector_all(selector)
            for node in nodes:
                try:
                    text = node.inner_text().strip()
                except PlaywrightError:
                    continue

                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue

                seen.add(key)
                comments.append(text)
                if len(comments) >= 20:
                    return comments

        return comments

    def _extract_signals(self, page: Page) -> List[str]:
        signals: List[str] = []
        seen: Set[str] = set()

        keywords = [
            "today",
            "yesterday",
            "new",
            "used",
            "pickup",
            "delivery",
            "sold",
            "negotiable",
            "available",
        ]

        for selector in self._config.selectors_post_signals:
            nodes = page.query_selector_all(selector)
            for node in nodes:
                try:
                    text = node.inner_text().strip()
                except PlaywrightError:
                    continue

                if not text:
                    continue
                lowered = text.lower()
                if not any(keyword in lowered for keyword in keywords):
                    continue
                if lowered in seen:
                    continue

                seen.add(lowered)
                signals.append(text)
                if len(signals) >= 15:
                    return signals

        return signals
