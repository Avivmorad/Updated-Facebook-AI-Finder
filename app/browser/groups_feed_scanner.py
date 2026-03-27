from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Dict, List, Optional, Sequence, Set
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from playwright.sync_api import ElementHandle
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.browser.facebook_access_adapter import FacebookAccessAdapter, FacebookAuthenticationRequiredError
from app.config.browser import BrowserConfig
from app.domain.posts import CandidatePostRef, SearchExecutionResult
from app.utils.app_errors import AppError, make_app_error, normalize_app_error
from app.utils.debugging import debug_app_error, debug_found, debug_info, debug_missing, debug_step, debug_warning
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


@dataclass
class _RoundScanStats:
    added: int = 0
    duplicates: int = 0
    invalid_links: int = 0
    unreadable_cards: int = 0


@dataclass
class _RawScanCandidate:
    href: str
    preview_text: str
    source: str


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
                logger.warning("Platform search attempt %s/%s failed: %s", attempt, max_attempts, app_error.code)
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
            raise make_app_error(code="ERR_GROUPS_FEED_OPEN_FAILED", technical_details=f"status={response.status}")
        if str(getattr(page, "url", "") or "").strip() == "about:blank":
            raise make_app_error(
                code="ERR_GROUPS_FEED_OPEN_FAILED",
                technical_details="groups_feed_ended_on_about_blank",
            )
        page.wait_for_timeout(1800)
        debug_found("DBG_GROUPS_FEED_OPEN_OK", "Groups feed opened successfully.")
        debug_info("DBG_GROUPS_FEED_URL", f"Groups feed current URL: {str(getattr(page, 'url', '') or '').strip()}")

    def _apply_feed_filters(self, page: Page) -> None:
        self._ensure_groups_feed_page(page)
        self._open_filters_panel_if_needed(page)
        debug_step("DBG_FILTER_RECENT_TRY", "Trying to apply filter: Recent posts.")
        recent_selected = self._try_select_recent_posts(page)
        recent_verified = self._verify_recent_filter_selected(page)
        if not recent_selected or not recent_verified:
            debug_warning("DBG_FILTER_RECENT_URL_FALLBACK", "Recent filter click path failed, trying URL fallback.")
            if self._apply_recent_filter_via_url(page):
                recent_verified = self._verify_recent_filter_selected(page)
        if not recent_selected and not recent_verified:
            recent_error = make_app_error(code="ERR_FILTER_RECENT_NOT_FOUND")
            debug_app_error(recent_error, include_technical_details=False)
            raise recent_error
        if not recent_verified:
            recent_error = make_app_error(code="ERR_FILTER_RECENT_NOT_FOUND")
            debug_app_error(recent_error, include_technical_details=False)
            raise recent_error
        debug_found("DBG_FILTER_RECENT_OK", "Filter 'Recent posts' was applied and verified.")
        self._ensure_groups_feed_page(page)

        debug_step("DBG_FILTER_24H_TRY", "Trying to apply filter: Last 24 hours.")
        last_24_selected = self._try_select_last_24_hours(page)
        if last_24_selected:
            debug_found("DBG_FILTER_24H_OK", "Filter 'Last 24 hours' was applied.")
        else:
            last24_error = make_app_error(code="ERR_FILTER_LAST24_NOT_FOUND")
            debug_missing(last24_error.code, last24_error.summary_he)
        debug_info("DBG_FILTERS_URL", f"Feed URL after filter step: {str(getattr(page, 'url', '') or '').strip()}")

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
                "\u05e4\u05d5\u05e1\u05d8\u05d9\u05dd \u05d0\u05d7\u05e8\u05d5\u05e0\u05d9\u05dd",
                "\u05d4\u05d7\u05d3\u05e9\u05d9\u05dd \u05d1\u05d9\u05d5\u05ea\u05e8",
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
                ["\u05d0\u05d7\u05e8\u05d5\u05e0"],
                ["\u05d7\u05d3\u05e9"],
            ],
            selected_event="platform_recent_posts_selected",
            not_found_event="platform_recent_posts_not_found",
        )

    def _try_select_last_24_hours(self, page: Page) -> bool:
        return self._try_select_page_option(
            page=page,
            selectors=self._config.selectors_last_24_hours,
            labels=[
                "24 \u05e9\u05e2\u05d5\u05ea \u05d0\u05d7\u05e8\u05d5\u05e0\u05d5\u05ea",
                "Last 24 hours",
                "Past 24 hours",
            ],
            keyword_groups=[
                ["24", "hour"],
                ["past", "24"],
                ["24", "\u05e9\u05e2\u05d5\u05ea"],
            ],
            selected_event="platform_last_24h_selected",
            not_found_event="platform_last_24h_not_found",
        )

    def _verify_recent_filter_selected(self, page: Page) -> bool:
        checks = (
            "\u05e4\u05d5\u05e1\u05d8\u05d9\u05dd \u05d0\u05d7\u05e8\u05d5\u05e0\u05d9\u05dd",
            "\u05d4\u05d7\u05d3\u05e9\u05d9\u05dd \u05d1\u05d9\u05d5\u05ea\u05e8",
            "Most recent",
            "Recent posts",
            "Newest",
            "Latest",
        )
        current_url = self._current_url(page)
        on_groups_feed = self._is_groups_feed_url(current_url)
        roles = ("button", "radio", "menuitem", "switch", "option")
        for label in checks:
            for role in roles:
                locator = page.get_by_role(role, name=label, exact=False)
                try:
                    count = min(locator.count(), 3)
                except PlaywrightError:
                    continue
                for index in range(count):
                    node = locator.nth(index)
                    if self._is_selected_node(node):
                        return True
        # Fallback signal: if the selected-state attributes are absent in current UI,
        # accept visible recent-filter labels after a successful click path.
        if on_groups_feed:
            for label in checks:
                try:
                    if page.get_by_text(label, exact=False).count() > 0:
                        return True
                except PlaywrightError:
                    continue
        current_url_lower = current_url.lower()
        if "sorting_setting=chronological" in current_url_lower and on_groups_feed:
            return True
        if "order=chronological" in current_url_lower and on_groups_feed:
            return True
        return False

    def _apply_recent_filter_via_url(self, page: Page) -> bool:
        goto = getattr(page, "goto", None)
        if not callable(goto):
            return False
        current_url = self._config.base_url
        candidates = (
            {"sorting_setting": "CHRONOLOGICAL"},
            {"order": "chronological"},
        )
        for query in candidates:
            try:
                parsed = urlparse(current_url)
                merged = dict(parse_qsl(parsed.query, keep_blank_values=True))
                merged.update(query)
                target = urlunparse(
                    (
                        parsed.scheme or "https",
                        parsed.netloc or "www.facebook.com",
                        parsed.path or "/groups/feed/",
                        parsed.params,
                        urlencode(merged, doseq=True),
                        "",
                    )
                )
                goto(target, wait_until="domcontentloaded", timeout=self._config.timeout_ms)
                page.wait_for_timeout(1200)
                log_event(logger, 20, "platform_recent_posts_selected", selector=f"url:{query}")
                if self._verify_recent_filter_selected(page):
                    return True
            except (PlaywrightError, ValueError):
                continue
        return False

    def _ensure_groups_feed_page(self, page: Page) -> None:
        current_url = self._current_url(page)
        if self._is_groups_feed_url(current_url):
            return
        goto = getattr(page, "goto", None)
        if not callable(goto):
            return
        debug_warning("DBG_GROUPS_FEED_RECOVER", f"Unexpected page during scan flow: {current_url}. Recovering to groups feed.")
        goto(self._config.base_url, wait_until="domcontentloaded", timeout=self._config.timeout_ms)
        page.wait_for_timeout(1200)

    def _is_groups_feed_url(self, url: str) -> bool:
        lowered = str(url or "").strip().lower()
        return "/groups/feed" in lowered

    def _current_url(self, page: Page) -> str:
        return str(getattr(page, "url", "") or "").strip()

    def _is_selected_node(self, node) -> bool:  # type: ignore[no-untyped-def]
        attr_names = ("aria-pressed", "aria-checked", "data-checked")
        for attr_name in attr_names:
            try:
                value = (node.get_attribute(attr_name) or "").strip().lower()
            except PlaywrightError:
                value = ""
            if value in {"true", "1"}:
                return True

        try:
            class_name = (node.get_attribute("class") or "").strip().lower()
        except PlaywrightError:
            class_name = ""
        return any(token in class_name for token in ("selected", "checked", "active"))

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
        if self._try_click_by_dom_keywords(page, keyword_groups, selected_event):
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

    def _try_click_by_dom_keywords(self, page: Page, keyword_groups: Sequence[Sequence[str]], selected_event: str) -> bool:
        dom_selectors = (
            "div[role='button']",
            "button",
            "label",
            "span[dir='auto']",
            "div[dir='auto']",
        )
        for selector in dom_selectors:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue
            for node in nodes[:400]:
                try:
                    text = (node.inner_text() or "").strip().lower()
                except PlaywrightError:
                    continue
                if not text:
                    continue
                if not any(all(keyword.lower() in text for keyword in group) for group in keyword_groups):
                    continue
                try:
                    node.click(timeout=1000)
                    page.wait_for_timeout(1200)
                    log_event(logger, 20, selected_event, selector=f"dom:{selector}:{text[:80]}")
                    return True
                except PlaywrightError:
                    continue
        return False

    def _scan_results(self, page: Page, max_posts: int) -> tuple[List[CandidatePostRef], List[str]]:
        items: List[CandidatePostRef] = []
        warnings: List[str] = []
        seen_links: Set[str] = set()

        for round_index in range(self._config.max_scroll_rounds):
            candidates = self._collect_round_candidates(page, warnings, round_index)
            before_round_count = len(items)
            stats = _RoundScanStats()
            if not candidates:
                debug_missing("DBG_SCAN_NO_CARDS", "No post cards found in this scan round.")

            for candidate in candidates:
                if len(items) >= max_posts:
                    return items, warnings

                normalized_url = self._normalize_post_link(candidate.href)
                if not normalized_url:
                    stats.invalid_links += 1
                    continue
                if normalized_url in seen_links:
                    stats.duplicates += 1
                    continue

                seen_links.add(normalized_url)
                stats.added += 1
                candidate_index = len(items) + 1
                debug_step("DBG_SCAN_POST", f"Scanning post {candidate_index} of {max_posts}.")
                items.append(
                    CandidatePostRef(
                        post_id=self._extract_post_id(normalized_url),
                        post_link=normalized_url,
                        preview_text=candidate.preview_text,
                        raw={
                            "post_link": normalized_url,
                            "preview_text": candidate.preview_text,
                            "scan_source": candidate.source,
                        },
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

            debug_info(
                "DBG_SCAN_ROUND_STATS",
                (
                    f"Round {round_index + 1}: added={stats.added}, duplicates={stats.duplicates}, "
                    f"invalid_links={stats.invalid_links}, unreadable={stats.unreadable_cards}."
                ),
            )

            if not self._load_more_or_scroll(page):
                break

        return items[:max_posts], warnings

    def _collect_round_candidates(
        self,
        page: Page,
        warnings: List[str],
        round_index: int,
    ) -> List[_RawScanCandidate]:
        candidates: List[_RawScanCandidate] = []
        seen_pairs: Set[tuple[str, str]] = set()
        direct_count = 0
        article_count = 0
        global_count = 0

        def _add(href: str, preview_text: str, source: str) -> None:
            nonlocal direct_count, article_count, global_count
            normalized_href = str(href or "").strip()
            if not normalized_href:
                return
            preview = str(preview_text or "").strip()
            key = (normalized_href, preview)
            if key in seen_pairs:
                return
            seen_pairs.add(key)
            candidates.append(_RawScanCandidate(href=normalized_href, preview_text=preview, source=source))
            if source == "direct_selector":
                direct_count += 1
            elif source == "article_anchor":
                article_count += 1
            else:
                global_count += 1

        direct_cards = self._query_result_cards(page)
        for card in direct_cards:
            try:
                href = (card.get_attribute("href") or "").strip()
                preview = (card.inner_text() or "").strip()
            except PlaywrightError as exc:
                warnings.append(f"skipped_unreadable_card:{str(exc)}")
                debug_warning("DBG_CARD_UNREADABLE", "Skipping unreadable post card.")
                continue
            _add(href, preview, "direct_selector")

        article_nodes = self._query_article_cards(page)
        for article in article_nodes[:400]:
            href = self._extract_best_post_href_from_article(article)
            if not href:
                continue
            try:
                preview = (article.inner_text() or "").strip()
            except PlaywrightError:
                preview = ""
            _add(href, preview, "article_anchor")

        try:
            link_nodes = page.query_selector_all("a[href]")
        except PlaywrightError:
            link_nodes = []
        for node in link_nodes[:1500]:
            try:
                href = (node.get_attribute("href") or "").strip()
                preview = (node.inner_text() or "").strip()
            except PlaywrightError:
                continue
            if not self._looks_like_post_link(href):
                continue
            _add(href, preview, "global_anchor")

        if round_index == 0:
            self._debug_dom_probe(page, len(direct_cards), len(article_nodes), len(candidates))
        debug_info(
            "DBG_SCAN_CANDIDATE_SOURCES",
            (
                f"Round {round_index + 1} candidate sources: "
                f"direct={direct_count}, article={article_count}, global={global_count}, total={len(candidates)}."
            ),
        )
        return candidates

    def _debug_dom_probe(
        self,
        page: Page,
        direct_card_count: int,
        article_count: int,
        candidate_count: int,
    ) -> None:
        try:
            total_anchors = len(page.query_selector_all("a[href]"))
        except PlaywrightError:
            total_anchors = 0
        debug_info(
            "DBG_SCAN_DOM_PROBE",
            (
                f"DOM probe: anchors={total_anchors}, direct_cards={direct_card_count}, "
                f"articles={article_count}, post_candidates={candidate_count}."
            ),
        )

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

    def _query_article_cards(self, page: Page):
        selectors = (
            "div[role='article']",
            "div[data-pagelet*='FeedUnit']",
            "div[aria-posinset]",
        )
        for selector in selectors:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue
            if nodes:
                return nodes
        return []

    def _extract_best_post_href_from_article(self, article: ElementHandle) -> str:
        try:
            anchors = article.query_selector_all("a[href]")
        except PlaywrightError:
            return ""

        best = ""
        for anchor in anchors[:120]:
            try:
                href = (anchor.get_attribute("href") or "").strip()
            except PlaywrightError:
                continue
            if not self._looks_like_post_link(href):
                continue
            if any(marker in href for marker in ("/posts/", "/permalink/", "story_fbid=", "fbid=", "/share/p/")):
                return href
            if not best:
                best = href
        return best

    def _looks_like_post_link(self, href: str) -> bool:
        text = str(href or "").strip()
        if not text:
            return False
        resolved = text
        if text.startswith("/"):
            resolved = f"https://www.facebook.com{text}"
        if not resolved.startswith("http"):
            return False

        try:
            parsed = urlparse(resolved)
        except ValueError:
            return False

        host = parsed.netloc.lower()
        if host and "facebook.com" not in host and "fb.com" not in host:
            return False

        path = parsed.path.lower()
        query = parsed.query.lower()
        if "/groups/" in path and "/posts/" in path:
            return True
        if "/permalink/" in path or "permalink.php" in path:
            return True
        if "/share/p/" in path:
            return True
        if "story_fbid=" in query and "id=" in query:
            return True
        if "fbid=" in query:
            return True
        return False

    def _normalize_post_link(self, href: str) -> str:
        text = href.strip()
        if not text:
            return ""

        resolved = text
        if text.startswith("/"):
            resolved = f"https://www.facebook.com{text}"
        if not resolved.startswith("http"):
            return ""
        if not self._looks_like_post_link(resolved):
            return ""

        try:
            parsed = urlparse(resolved)
            host = parsed.netloc.lower()
            if host and "facebook.com" not in host and "fb.com" not in host:
                return ""
            query_items = parse_qsl(parsed.query, keep_blank_values=True)
            kept = [
                (k, v)
                for (k, v) in query_items
                if not k.startswith("__") and k not in {"notif_id", "notif_t", "ref", "acontext"}
            ]
            clean_query = urlencode(kept, doseq=True)
            return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, parsed.params, clean_query, ""))
        except ValueError:
            return resolved

    def _extract_post_id(self, url: str) -> str:
        for marker in ("/posts/", "/permalink/"):
            if marker not in url:
                continue
            suffix = url.split(marker, 1)[1]
            post_id = suffix.split("/", 1)[0].split("?", 1)[0]
            if post_id:
                return post_id
        return url.rstrip("/").rsplit("/", 1)[-1] or "unknown-post"
