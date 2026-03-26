from time import sleep
from typing import List, Optional, Set

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
        result = SearchExecutionResult()
        log_event(logger, 20, "platform_search_started", query_text=query_text, max_posts=max_posts)
        debug_step("DBG_GROUPS_SCAN_START", "מתחיל סריקה של פיד הקבוצות בפייסבוק.")

        max_attempts = self._config.retries + 1
        for attempt in range(1, max_attempts + 1):
            result.attempts = attempt
            debug_info("DBG_GROUPS_SCAN_ATTEMPT", f"ניסיון סריקה {attempt}/{max_attempts}.")
            try:
                with self._facebook_access.authenticated_session() as session:
                    page = session.page
                    self._open_platform(page)
                    self._navigate_to_search_area(page, query_text)
                    items, warnings = self._scan_results(page, max_posts)
                    result.items = items
                    result.warnings.extend(warnings)
                    if items:
                        debug_found("DBG_GROUPS_SCAN_DONE", f"הסריקה אספה {len(items)} קישורי פוסטים ייחודיים.")
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
                    default_summary_he="סריקת פיד הקבוצות נכשלה",
                    default_cause_he="אירעה שגיאה במהלך ניסיון הסריקה",
                    default_action_he="בדוק חיבור, התחברות לפייסבוק ונסה שוב",
                )
                result.warnings.append(app_error.code)
                logger.warning(
                    "Platform search attempt %s/%s failed: %s",
                    attempt,
                    max_attempts,
                    app_error.code,
                )
                debug_app_error(app_error)
                if attempt < max_attempts:
                    debug_warning("DBG_GROUPS_SCAN_RETRY", "הסריקה נכשלה, מבצע ניסיון נוסף.")
                    sleep(min(1.5, 0.3 * attempt))

        final_error = make_app_error(code="ERR_GROUPS_SCAN_FAILED")
        result.fatal_error = final_error.code
        debug_app_error(final_error)
        return result

    def _open_platform(self, page: Page) -> None:
        debug_step("DBG_GROUPS_FEED_OPEN", "עובר לפיד הקבוצות שלי בפייסבוק.")
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
        debug_found("DBG_GROUPS_FEED_OPEN_OK", "פיד הקבוצות נפתח בהצלחה.")

    def _navigate_to_search_area(self, page: Page, query_text: str) -> None:
        debug_step("DBG_SEARCH_QUERY_TRY", "מנסה למלא את תיבת החיפוש של פייסבוק.")
        searched = self._try_search_input_navigation(page, query_text)
        debug_step("DBG_FILTER_RECENT_TRY", "מנסה לסמן פילטר: פוסטים אחרונים.")
        recent_selected = self._try_select_recent_posts(page)
        debug_step("DBG_FILTER_24H_TRY", "מנסה לסמן פילטר: 24 שעות אחרונות.")
        last_24_selected = self._try_select_last_24_hours(page)

        if searched:
            debug_found("DBG_SEARCH_QUERY_OK", "השאילתה הוזנה בתיבת החיפוש.")
        else:
            debug_warning("DBG_SEARCH_QUERY_MISSING", "לא נמצאה תיבת חיפוש מתאימה, ממשיך לסריקה גלויה.")

        if recent_selected:
            debug_found("DBG_FILTER_RECENT_OK", "הפילטר 'פוסטים אחרונים' סומן בהצלחה.")
        else:
            recent_error = make_app_error(code="ERR_FILTER_RECENT_NOT_FOUND")
            debug_missing(recent_error.code, recent_error.summary_he)

        if last_24_selected:
            debug_found("DBG_FILTER_24H_OK", "הפילטר '24 שעות אחרונות' סומן בהצלחה.")
        else:
            last24_error = make_app_error(code="ERR_FILTER_LAST24_NOT_FOUND")
            debug_missing(last24_error.code, last24_error.summary_he)

    def _try_select_recent_posts(self, page: Page) -> bool:
        return self._try_select_page_option(
            page=page,
            selectors=self._config.selectors_recent_posts,
            labels=["פוסטים אחרונים", "Most recent", "Recent posts"],
            selected_event="platform_recent_posts_selected",
            not_found_event="platform_recent_posts_not_found",
        )

    def _try_select_last_24_hours(self, page: Page) -> bool:
        return self._try_select_page_option(
            page=page,
            selectors=self._config.selectors_last_24_hours,
            labels=["24 שעות אחרונות", "Last 24 hours"],
            selected_event="platform_last_24h_selected",
            not_found_event="platform_last_24h_not_found",
        )

    def _try_select_page_option(
        self,
        page: Page,
        selectors: List[str],
        labels: List[str],
        selected_event: str,
        not_found_event: str,
    ) -> bool:
        if self._try_click_by_selectors(page, selectors, selected_event):
            return True
        if self._try_click_by_labels(page, labels, selected_event):
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
        return False

    def _try_search_input_navigation(self, page: Page, query_text: str) -> bool:
        node = self._find_first_selector(page, self._config.selectors_search_input)
        if node is None:
            return False

        try:
            node.click(timeout=1000)
            node.fill(query_text, timeout=self._config.timeout_ms)
            node.press("Enter", timeout=1000)
            page.wait_for_timeout(1500)
            return True
        except PlaywrightError:
            return False

    def _scan_results(self, page: Page, max_posts: int) -> tuple[List[CandidatePostRef], List[str]]:
        items: List[CandidatePostRef] = []
        warnings: List[str] = []
        seen_links: Set[str] = set()

        for round_index in range(self._config.max_scroll_rounds):
            cards = self._query_result_cards(page)
            before_round_count = len(items)
            if not cards:
                debug_missing("DBG_SCAN_NO_CARDS", "לא נמצאו כרטיסי פוסטים בסבב הסריקה הנוכחי.")

            for card in cards:
                if len(items) >= max_posts:
                    return items, warnings

                try:
                    href = (card.get_attribute("href") or "").strip()
                    card_text = (card.inner_text() or "").strip()
                except PlaywrightError as exc:
                    warnings.append(f"skipped_unreadable_card:{str(exc)}")
                    debug_warning("DBG_CARD_UNREADABLE", "דילוג על כרטיס פוסט שלא ניתן לקריאה.")
                    continue

                normalized_url = self._normalize_post_link(href)
                if not normalized_url or normalized_url in seen_links:
                    continue

                seen_links.add(normalized_url)
                candidate_index = len(items) + 1
                debug_step("DBG_SCAN_POST", f"סורק פוסט {candidate_index} מתוך {max_posts}.")
                items.append(
                    CandidatePostRef(
                        post_id=self._extract_post_id(normalized_url),
                        post_link=normalized_url,
                        preview_text=card_text,
                        raw={"post_link": normalized_url, "preview_text": card_text},
                    )
                )
                debug_found("DBG_POST_FOUND", f"נמצא קישור לפוסט: {normalized_url}")

            if len(items) >= max_posts:
                return items, warnings

            added_this_round = len(items) - before_round_count
            if added_this_round == 0:
                debug_missing(
                    "DBG_SCROLL_NO_NEW",
                    f"סבב גלילה {round_index + 1}/{self._config.max_scroll_rounds}: לא נוספו פוסטים חדשים.",
                )
            else:
                debug_info(
                    "DBG_SCROLL_PROGRESS",
                    (
                        f"סבב גלילה {round_index + 1}/{self._config.max_scroll_rounds}: "
                        f"נוספו {added_this_round}, סה\"כ {len(items)}."
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
                debug_step("DBG_SCROLL_CLICK", "מנסה ללחוץ על כפתור 'עוד/Load more'.")
                button.click(timeout=1000)
                page.wait_for_timeout(self._config.scroll_pause_ms)
                return True
            except PlaywrightError:
                continue

        debug_step("DBG_SCROLL_WHEEL", "לא נמצא כפתור 'עוד', מבצע גלילה ידנית מטה.")
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

    def _normalize_post_link(self, href: str) -> str:
        text = href.strip()
        if not text:
            return ""
        if text.startswith("http"):
            return text
        if text.startswith("/"):
            return f"https://www.facebook.com{text}"
        return ""

    def _extract_post_id(self, url: str) -> str:
        for marker in ["/posts/", "/permalink/"]:
            if marker not in url:
                continue
            suffix = url.split(marker, 1)[1]
            post_id = suffix.split("/", 1)[0].split("?", 1)[0]
            if post_id:
                return post_id
        return url.rstrip("/").rsplit("/", 1)[-1] or "unknown-post"
