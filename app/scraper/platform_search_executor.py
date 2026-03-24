import re
from typing import Dict, List, Optional, Set
from urllib.parse import quote
from time import sleep

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.models.scraper_models import RawSearchResultRef, SearchExecutionResult
from app.scraper.facebook_access_adapter import FacebookAccessAdapter, FacebookAuthenticationRequiredError
from app.utils.logger import get_logger, log_event
from config.platform_access_config import PlatformAccessConfig


logger = get_logger(__name__)
_PRICE_LINE_REGEX = re.compile(r"(?:[₪$€]|usd|ils|eur)|\d")


class PlatformSearchExecutor:
    def __init__(self, config: Optional[PlatformAccessConfig] = None) -> None:
        self._config = config or PlatformAccessConfig()
        self._facebook_access = FacebookAccessAdapter(self._config)

    def execute_search(self, query_text: str, max_posts: int) -> SearchExecutionResult:
        result = SearchExecutionResult()
        log_event(logger, 20, "platform_search_started", query_text=query_text, max_posts=max_posts)

        for attempt in range(1, self._config.retries + 2):
            result.attempts = attempt
            try:
                log_event(logger, 20, "platform_search_attempt", attempt=attempt)
                with self._facebook_access.authenticated_session() as session:
                    page = session.page
                    self._open_platform(page)
                    self._navigate_to_search_area(page, query_text)

                    items, warnings = self._scan_results(page=page, max_posts=max_posts)
                    result.items = items
                    result.warnings.extend(warnings)

                    if not items:
                        result.warnings.append("No results detected in current page state")

                    log_event(
                        logger,
                        20,
                        "platform_search_finished",
                        attempt=attempt,
                        items=len(items),
                        warnings=len(result.warnings),
                    )

                    return result
            except FacebookAuthenticationRequiredError as exc:
                result.warnings.append(str(exc))
                result.fatal_error = str(exc)
                log_event(logger, 40, "platform_search_authentication_required", attempt=attempt, message=str(exc))
                return result
            except (PlaywrightTimeoutError, PlaywrightError, RuntimeError) as exc:
                message = f"attempt {attempt} failed: {str(exc)}"
                result.warnings.append(message)
                logger.warning("Platform search failure: %s", message)
                if attempt < self._config.retries + 1:
                    # Small bounded backoff between retries to reduce transient flakiness.
                    delay_ms = min(1500, 300 * attempt)
                    sleep(delay_ms / 1000.0)

        result.fatal_error = (
            "Failed to execute platform search after retries. "
            + (result.warnings[-1] if result.warnings else "Unknown error")
        )
        log_event(logger, 40, "platform_search_failed", attempts=result.attempts, fatal_error=result.fatal_error)
        return result

    def _open_platform(self, page: Page) -> None:
        current_url = str(getattr(page, "url", "") or "").strip()
        log_event(logger, 20, "platform_open_requested", current_url=current_url, target_url=self._config.base_url)
        response = page.goto(
            self._config.base_url,
            wait_until="domcontentloaded",
            timeout=self._config.timeout_ms,
        )
        if response is not None and not response.ok:
            raise RuntimeError(f"platform page load failed with status {response.status}")
        final_url = str(getattr(page, "url", "") or "").strip()
        log_event(
            logger,
            20,
            "platform_open_completed",
            final_url=final_url,
            http_status=response.status if response is not None else "none",
        )
        if final_url == "about:blank":
            raise RuntimeError("platform open ended on about:blank")

    def _navigate_to_search_area(self, page: Page, query_text: str) -> None:
        self._navigate_by_query_url(page, query_text, reason="direct_query_navigation")

    def _navigate_by_query_url(self, page: Page, query_text: str, reason: str) -> None:
        query_url = f"{self._config.base_url}/search?query={quote(query_text)}"
        current_url = str(getattr(page, "url", "") or "").strip()
        log_event(
            logger,
            20,
            "platform_query_url_navigation",
            current_url=current_url,
            query_url=query_url,
            reason=reason,
        )
        response = page.goto(query_url, wait_until="domcontentloaded", timeout=self._config.timeout_ms)
        if response is not None and not response.ok:
            raise RuntimeError(f"search page load failed with status {response.status}")
        final_url = str(getattr(page, "url", "") or "").strip()
        log_event(
            logger,
            20,
            "platform_query_url_navigation_completed",
            final_url=final_url,
            http_status=response.status if response is not None else "none",
            query_url=query_url,
        )
        if final_url == "about:blank":
            raise RuntimeError("search query navigation ended on about:blank")

    def _scan_results(self, page: Page, max_posts: int) -> tuple[List[RawSearchResultRef], List[str]]:
        items: List[RawSearchResultRef] = []
        warnings: List[str] = []
        seen_keys: Set[str] = set()

        for _ in range(self._config.max_scroll_rounds):
            cards = self._query_result_cards(page)

            for card in cards:
                if len(items) >= max_posts:
                    return items, warnings

                try:
                    href = card.get_attribute("href") or ""
                    card_text = (card.inner_text() or "").strip()
                    parsed_card = self._parse_card_text(card_text)
                    title = self._extract_text_from_element(card, self._config.selectors_title) or ""
                    if self._looks_like_price_or_generic(title):
                        title = parsed_card.get("title", "")

                    if not href and not title and not card_text:
                        continue

                    normalized_url = href if href.startswith("http") else f"https://www.facebook.com{href}"
                    post_id = self._extract_post_id(normalized_url, fallback_title=title)
                    dedupe_key = normalized_url or post_id
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)

                    price_text = self._extract_text_from_element(card, self._config.selectors_price)
                    if not price_text or not self._looks_like_price(price_text):
                        price_text = parsed_card.get("price_text")

                    region_text = self._extract_text_from_element(card, self._config.selectors_region)
                    if not region_text or self._looks_like_price_or_generic(region_text):
                        region_text = parsed_card.get("region")

                    snippet = parsed_card.get("summary") or title

                    items.append(
                        RawSearchResultRef(
                            post_id=post_id,
                            title=title or post_id,
                            url=normalized_url,
                            snippet=snippet,
                            price_text=price_text,
                            region=region_text,
                            raw={
                                "url": normalized_url,
                                "title": title,
                                "card_text": card_text,
                                "price_text": price_text,
                                "region": region_text,
                            },
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"Skipped malformed result card: {str(exc)}")

            if len(items) >= max_posts:
                return items, warnings

            moved = self._load_more_or_scroll(page)
            if not moved:
                break

        return items[:max_posts], warnings

    def _load_more_or_scroll(self, page: Page) -> bool:
        for selector in self._config.selectors_load_more:
            button = page.query_selector(selector)
            if button is not None:
                try:
                    button.click(timeout=1000)
                    page.wait_for_timeout(self._config.scroll_pause_ms)
                    return True
                except PlaywrightError:
                    continue

        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(self._config.scroll_pause_ms)
        return True

    def _query_result_cards(self, page: Page):
        for selector in self._config.selectors_result_cards:
            nodes = page.query_selector_all(selector)
            if nodes:
                return nodes
        return []

    def _find_first_selector(self, page: Page, selectors: List[str]):
        for selector in selectors:
            node = page.query_selector(selector)
            if node is not None:
                return node
        return None

    def _extract_text_from_element(self, element, selectors: List[str]) -> Optional[str]:
        for selector in selectors:
            node = element.query_selector(selector)
            if node is None:
                continue
            text = node.inner_text().strip()
            if text:
                return text
        text = element.inner_text().strip()
        return text if text else None

    def _extract_post_id(self, url: str, fallback_title: str) -> str:
        marker = "/marketplace/item/"
        if marker in url:
            suffix = url.split(marker, 1)[1]
            post_id = suffix.split("/", 1)[0].split("?", 1)[0]
            if post_id:
                return post_id

        normalized_title = "-".join(fallback_title.lower().split())
        return normalized_title[:60] if normalized_title else "unknown-post"

    def _parse_card_text(self, card_text: str) -> Dict[str, str]:
        lines = [line.strip() for line in card_text.splitlines() if line.strip()]
        if not lines:
            return {}

        price_line = next((line for line in lines if self._looks_like_price(line)), "")
        non_price_lines = [line for line in lines if line != price_line]
        title_line = non_price_lines[0] if non_price_lines else ""
        region_line = non_price_lines[-1] if len(non_price_lines) >= 2 else ""
        summary_line = " ".join(non_price_lines[:2]).strip() or title_line or price_line

        return {
            "price_text": price_line,
            "title": title_line,
            "region": region_line,
            "summary": summary_line,
        }

    def _looks_like_price(self, value: Optional[str]) -> bool:
        text = str(value or "").strip().lower()
        if not text:
            return False
        return bool(_PRICE_LINE_REGEX.search(text))

    def _looks_like_price_or_generic(self, value: Optional[str]) -> bool:
        text = str(value or "").strip().lower()
        if not text:
            return True
        if self._looks_like_price(text):
            return True
        generic_markers = {"marketplace", "פורסמו ממש עכשיו", "just listed"}
        return text in generic_markers
