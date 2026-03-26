from time import sleep
from typing import List, Optional, Sequence, Set
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.browser.facebook_access_adapter import FacebookAccessAdapter, FacebookAuthenticationRequiredError
from app.config.browser import BrowserConfig
from app.domain.posts import CandidatePostRef, SearchExecutionResult
from app.utils.app_errors import AppError, make_app_error, normalize_app_error
from app.utils.debugging import (
    debug_app_error,
    debug_found,
    debug_info,
    debug_missing,
    debug_step,
    debug_warning,
)
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class GroupsFeedScanner:
    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self._config = config or BrowserConfig()
        self._facebook_access = FacebookAccessAdapter(self._config)

    def execute_search(self, query_text: str, max_posts: int) -> SearchExecutionResult:
        _ = query_text
        result = SearchExecutionResult()
        log_event(logger, 20, "platform_search_started", max_posts=max_posts)
        debug_step("DBG_GROUPS_SCAN_START", "Starting groups feed scan on Facebook.")

        max_attempts = self._config.retries + 1
        for attempt in range(1, max_attempts + 1):
            result.attempts = attempt
            debug_info("DBG_GROUPS_SCAN_ATTEMPT", f"Scan attempt {attempt}/{max_attempts}.")
            try:
                with self._facebook_access.authenticated_session() as session:
                    page = session.page
                    self._open_platform(page)
                    self._apply_feed_filters(page)
                    items, warnings = self._scan_results(page, max_posts)
                    result.items = items
                    result.warnings.extend(warnings)
                    if items:
                        debug_found("DBG_GROUPS_SCAN_DONE", f"Scan collected {len(items)} unique post link(s).")
                    else:
                        missing_error = make_app_error(code="ERR_NO_POST_LINKS_FOUND")
                        result.warnings.append(missing_error.code)
                        debug_missing(missing_error.code, missing_error.summary_he)
                    return result
            except FacebookAuthenticationRequiredError as exc:
                result.fatal_error = exc.app_error.code
                result.warnings.append(exc.app_error.code)
                debug_app_error(exc.app_error)
                return result
            except (PlaywrightTimeoutError, PlaywrightError, RuntimeError, AppError) as exc:
                app_error = normalize_app_error(
                    exc,
                    default_code="ERR_GROUPS_SCAN_FAILED",
                    default_summary_he="Groups feed scan failed",
                    default_cause_he="An error occurred during scan attempt",
                    default_action_he="Check connection and Facebook session, then retry",
                )
                result.warnings.append(app_error.code)
                logger.warning(
                    "Platform search attempt %s/%s failed: %s",
                    attempt,
                    max_attempts,
                    app_error.code,
                )
                debug_app_error(app_error)

                if app_error.code == "ERR_FILTER_RECENT_NOT_FOUND":
                    result.fatal_error = app_error.code
                    return result

                if attempt < max_attempts:
                    debug_warning("DBG_GROUPS_SCAN_RETRY", "Scan failed, retrying.")
                    sleep(min(1.5, 0.3 * attempt))

        final_error = make_app_error(code="ERR_GROUPS_SCAN_FAILED")
        result.fatal_error = final_error.code
        debug_app_error(final_error)
        return result

    def _open_platform(self, page: Page) -> None:
        debug_step("DBG_GROUPS_FEED_OPEN", "Opening Facebook Groups feed.")
        response = page.goto(
            self._config.base_url,
            wait_until="domcontentloaded",
            timeout=self._config.timeout_ms,
        )
        if response is not None and not response.ok:
            raise make_app_error(
                code="ERR_GROUPS_FEED_OPEN_FAILED",
                technical_details=f"status={response.status}",
            )
        if str(getattr(page, "url", "") or "").strip() == "about:blank":
            raise make_app_error(
                code="ERR_GROUPS_FEED_OPEN_FAILED",
                technical_details="groups_feed_ended_on_about_blank",
            )
        debug_found("DBG_GROUPS_FEED_OPEN_OK", "Groups feed opened successfully.")

    def _apply_feed_filters(self, page: Page) -> None:
        self._open_filters_panel_if_needed(page)
        debug_step("DBG_FILTER_RECENT_TRY", "Trying to apply filter: Recent posts.")
        recent_selected = self._try_select_recent_posts(page)
        if not recent_selected:
            recent_error = make_app_error(code="ERR_FILTER_RECENT_NOT_FOUND")
            debug_app_error(recent_error, include_technical_details=False)
            raise recent_error
        debug_found("DBG_FILTER_RECENT_OK", "Filter 'Recent posts' was applied.")

        debug_step("DBG_FILTER_24H_TRY", "Trying to apply filter: Last 24 hours.")
        last_24_selected = self._try_select_last_24_hours(page)
        if last_24_selected:
            debug_found("DBG_FILTER_24H_OK", "Filter 'Last 24 hours' was applied.")
        else:
            last24_error = make_app_error(code="ERR_FILTER_LAST24_NOT_FOUND")
            debug_missing(last24_error.code, last24_error.summary_he)

    def _open_filters_panel_if_needed(self, page: Page) -> None:
        for selector in self._config.selectors_filters_panel:
            button = page.query_selector(selector)
            if button is None:
                continue
            try:
                button.click(timeout=1200)
                page.wait_for_timeout(1000)
                debug_found("DBG_FILTER_PANEL_OPEN", "Opened filters panel.")
                return
            except PlaywrightError:
                continue

    def _try_select_recent_posts(self, page: Page) -> bool:
        return self._try_select_page_option(
            page=page,
            selectors=self._config.selectors_recent_posts,
            labels=[
                "פוסטים אחרונים",
                "פוסטים חדשים",
                "Most recent",
                "Recent posts",
                "Newest",
                "Latest",
                "Most recent first",
                "Chronological",
            ],
            keyword_groups=[
                ["recent"],
                ["latest"],
                ["newest"],
                ["chronological"],
                ["אחרונ"],
                ["חדש"],
            ],
            selected_event="platform_recent_posts_selected",
            not_found_event="platform_recent_posts_not_found",
        )

    def _try_select_last_24_hours(self, page: Page) -> bool:
        return self._try_select_page_option(
            page=page,
            selectors=self._config.selectors_last_24_hours,
            labels=[
                "24 שעות אחרונות",
                "24 השעות האחרונות",
                "Last 24 hours",
                "Past 24 hours",
            ],
            keyword_groups=[
                ["24", "hour"],
                ["past", "24"],
                ["24", "שעות"],
            ],
            selected_event="platform_last_24h_selected",
            not_found_event="platform_last_24h_not_found",
        )

    def _try_select_page_option(
        self,
        page: Page,
        selectors: List[str],
        labels: List[str],
        keyword_groups: Sequence[Sequence[str]],
        selected_event: str,
        not_found_event: str,
    ) -> bool:
        if self._try_click_by_selectors(page, selectors, selected_event):
            return True
        if self._try_click_by_labels(page, labels, selected_event):
            return True
        if self._try_click_by_keywords(page, keyword_groups, selected_event):
            return True
        log_event(logger, 20, not_found_event)
        return False

    def _try_click_by_selectors(self, page: Page, selectors: List[str], selected_event: str) -> bool:
        for selector in selectors:
            node = page.query_selector(selector)
            if node is None:
                continue
            try:
                node.click(timeout=1200)
                page.wait_for_timeout(1200)
                log_event(logger, 20, selected_event, selector=selector)
                return True
            except PlaywrightError:
                continue
        return False

    def _try_click_by_labels(self, page: Page, labels: List[str], selected_event: str) -> bool:
        roles = ["button", "switch", "menuitem", "radio", "option", "link"]
        for label in labels:
            for role in roles:
                locator = page.get_by_role(role, name=label, exact=False).first
                try:
                    if locator.count() == 0:
                        continue
                    locator.click(timeout=1200)
                    page.wait_for_timeout(1200)
                    log_event(logger, 20, selected_event, selector=f"role:{role}:{label}")
                    return True
                except PlaywrightError:
                    continue
            text_locator = page.get_by_text(label, exact=False).first
            try:
                if text_locator.count() == 0:
                    continue
                text_locator.click(timeout=1200)
                page.wait_for_timeout(1200)
                log_event(logger, 20, selected_event, selector=f"text:{label}")
                return True
            except PlaywrightError:
                continue
        return False

    def _try_click_by_keywords(self, page: Page, keyword_groups: Sequence[Sequence[str]], selected_event: str) -> bool:
        if not keyword_groups:
            return False
        roles = ["button", "link", "menuitem", "radio", "option"]
        for role in roles:
            locator = page.get_by_role(role)
            try:
                count = min(locator.count(), 300)
            except PlaywrightError:
                continue
            for index in range(count):
                node = locator.nth(index)
                try:
                    text = (node.inner_text(timeout=300) or "").strip().lower()
                except PlaywrightError:
                    continue
                if not text:
                    continue
                if any(all(keyword.lower() in text for keyword in group) for group in keyword_groups):
                    try:
                        node.click(timeout=1200)
                        page.wait_for_timeout(1200)
                        log_event(logger, 20, selected_event, selector=f"keyword:{role}:{text[:80]}")
                        return True
                    except PlaywrightError:
                        continue
        return False

    def _scan_results(self, page: Page, max_posts: int) -> tuple[List[CandidatePostRef], List[str]]:
        items: List[CandidatePostRef] = []
        warnings: List[str] = []
        seen_links: Set[str] = set()

        for round_index in range(self._config.max_scroll_rounds):
            cards = self._query_result_cards(page)
            before_round_count = len(items)
            if not cards:
                debug_missing("DBG_SCAN_NO_CARDS", "No post cards found in this scan round.")

            for card in cards:
                if len(items) >= max_posts:
                    return items, warnings

                try:
                    href = (card.get_attribute("href") or "").strip()
                    card_text = (card.inner_text() or "").strip()
                except PlaywrightError as exc:
                    warnings.append(f"skipped_unreadable_card:{str(exc)}")
                    debug_warning("DBG_CARD_UNREADABLE", "Skipping unreadable post card.")
                    continue

                normalized_url = self._normalize_post_link(href)
                if not normalized_url or normalized_url in seen_links:
                    continue

                seen_links.add(normalized_url)
                candidate_index = len(items) + 1
                debug_step("DBG_SCAN_POST", f"Scanning post {candidate_index} of {max_posts}.")
                items.append(
                    CandidatePostRef(
                        post_id=self._extract_post_id(normalized_url),
                        post_link=normalized_url,
                        preview_text=card_text,
                        raw={"post_link": normalized_url, "preview_text": card_text},
                    )
                )
                debug_found("DBG_POST_FOUND", f"Found post link: {normalized_url}")

            if len(items) >= max_posts:
                return items, warnings

            added_this_round = len(items) - before_round_count
            if added_this_round == 0:
                debug_missing(
                    "DBG_SCROLL_NO_NEW",
                    f"Scroll round {round_index + 1}/{self._config.max_scroll_rounds}: no new posts.",
                )
            else:
                debug_info(
                    "DBG_SCROLL_PROGRESS",
                    (
                        f"Scroll round {round_index + 1}/{self._config.max_scroll_rounds}: "
                        f"added {added_this_round}, total {len(items)}."
                    ),
                )

            if not self._load_more_or_scroll(page):
                break

        return items[:max_posts], warnings

    def _load_more_or_scroll(self, page: Page) -> bool:
        for selector in self._config.selectors_load_more:
            button = page.query_selector(selector)
            if button is None:
                continue
            try:
                debug_step("DBG_SCROLL_CLICK", "Trying to click 'See more / Load more' button.")
                button.click(timeout=1000)
                page.wait_for_timeout(self._config.scroll_pause_ms)
                return True
            except PlaywrightError:
                continue

        debug_step("DBG_SCROLL_WHEEL", "No 'Load more' button found; using manual scroll.")
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(self._config.scroll_pause_ms)
        return True

    def _query_result_cards(self, page: Page):
        for selector in self._config.selectors_result_cards:
            nodes = page.query_selector_all(selector)
            if nodes:
                return nodes
        return []

    def _normalize_post_link(self, href: str) -> str:
        text = href.strip()
        if not text:
            return ""

        resolved = text
        if text.startswith("/"):
            resolved = f"https://www.facebook.com{text}"
        if not resolved.startswith("http"):
            return ""

        try:
            parsed = urlparse(resolved)
            query_items = parse_qsl(parsed.query, keep_blank_values=True)
            kept = [
                (k, v)
                for (k, v) in query_items
                if not k.startswith("__") and k not in {"notif_id", "notif_t", "ref", "acontext"}
            ]
            clean_query = urlencode(kept, doseq=True)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, clean_query, ""))
        except ValueError:
            return resolved

    def _extract_post_id(self, url: str) -> str:
        for marker in ["/posts/", "/permalink/"]:
            if marker not in url:
                continue
            suffix = url.split(marker, 1)[1]
            post_id = suffix.split("/", 1)[0].split("?", 1)[0]
            if post_id:
                return post_id
        return url.rstrip("/").rsplit("/", 1)[-1] or "unknown-post"
