from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import ElementHandle
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.browser.facebook_access_adapter import FacebookAccessAdapter, FacebookAuthenticationRequiredError
from app.config.browser import BrowserConfig
from app.domain.posts import PostExtractionResult
from app.extraction.post_normalizer import normalize_post_data
from app.utils.app_errors import AppError, make_app_error, normalize_app_error
from app.utils.debugging import debug_app_error, debug_found, debug_info, debug_missing, debug_step, debug_warning
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
            link_error = make_app_error(code="ERR_POST_LINK_MISSING")
            result.error = link_error.code
            result.warnings.append(link_error.code)
            debug_app_error(link_error, include_technical_details=False)
            return result

        attempts = max(1, self._config.retries + 1)
        last_error = make_app_error(code="ERR_POST_PAGE_LOAD_FAILED")
        debug_step("DBG_POST_OPEN", "Opening post page to extract text, images, and publish date.")

        for attempt in range(1, attempts + 1):
            try:
                with self._facebook_access.authenticated_session() as session:
                    page = session.page
                    debug_info("DBG_POST_OPEN_ATTEMPT", f"Post extraction attempt {attempt}/{attempts}: {post_link}")
                    final_link = self._open_post_page(page, post_link)
                    self._expand_post_text(page)
                    raw = self._extract_raw_post(page, post_link=final_link, fallback_post_id=post_id)
                    result.raw_post_data = raw
                    result.normalized_post_data = normalize_post_data(raw)
                    if attempt > 1:
                        result.warnings.append(f"post_extraction_retry_success:{attempt}")

                    if result.normalized_post_data.get("post_text"):
                        debug_found("DBG_POST_TEXT_OK", "Post text was found.")
                    else:
                        missing_text = make_app_error(code="ERR_POST_TEXT_NOT_FOUND")
                        result.warnings.append(missing_text.code)
                        debug_missing(missing_text.code, missing_text.summary_he)

                    image_count = int(result.normalized_post_data.get("image_count", 0))
                    if image_count > 0:
                        debug_found("DBG_POST_IMAGES_OK", f"Found {image_count} image(s).")
                    else:
                        missing_images = make_app_error(code="ERR_POST_IMAGES_NOT_FOUND")
                        result.warnings.append(missing_images.code)
                        debug_missing(missing_images.code, missing_images.summary_he)

                    if result.normalized_post_data.get("publish_date_normalized") or result.normalized_post_data.get(
                        "publish_date_raw"
                    ):
                        debug_found("DBG_POST_DATE_OK", "Publish date was found.")
                    else:
                        missing_date = make_app_error(code="ERR_POST_PUBLISH_DATE_MISSING")
                        result.warnings.append(missing_date.code)
                        debug_missing(missing_date.code, missing_date.summary_he)

                    debug_found("DBG_POST_EXTRACT_OK", "Post extraction completed successfully.")
                    return result
            except FacebookAuthenticationRequiredError as exc:
                last_error = exc.app_error
                result.warnings.append(last_error.code)
                debug_app_error(last_error)
                break
            except (PlaywrightTimeoutError, PlaywrightError, RuntimeError, AppError) as exc:
                last_error = normalize_app_error(
                    exc,
                    default_code="ERR_POST_PAGE_LOAD_FAILED",
                    default_summary_he="Post page load failed",
                    default_cause_he="An error occurred while navigating or loading the post page",
                    default_action_he="Retry and verify the post link is valid and accessible",
                )
                result.warnings.append(f"extraction_attempt_{attempt}_failed")
                logger.warning("Post extraction attempt %s/%s failed for %s: %s", attempt, attempts, post_link, str(last_error))
                debug_app_error(last_error)
                debug_warning("DBG_POST_EXTRACT_RETRY", f"Post extraction failed on attempt {attempt}/{attempts}.")

        result.success = False
        result.error = last_error.code
        debug_app_error(last_error)
        return result

    def _open_post_page(self, page: Page, post_link: str) -> str:
        response = page.goto(post_link, wait_until="domcontentloaded", timeout=self._config.timeout_ms)
        if response is not None and not response.ok:
            raise make_app_error(
                code="ERR_POST_PAGE_LOAD_FAILED",
                technical_details=f"post_link={post_link} status={response.status}",
            )
        final_url = str(getattr(page, "url", "") or "").strip()
        if final_url == "about:blank":
            raise make_app_error(
                code="ERR_POST_PAGE_LOAD_FAILED",
                technical_details=f"post_link={post_link} ended_on=about:blank",
            )

        page.wait_for_timeout(1200)
        for selector in self._config.selectors_post_ready:
            try:
                page.wait_for_selector(selector, timeout=self._config.timeout_ms)
                break
            except PlaywrightTimeoutError:
                continue
        return final_url or post_link

    def _expand_post_text(self, page: Page) -> None:
        for selector in self._config.selectors_expand_post_text:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue
            for node in nodes[:3]:
                try:
                    if not node.is_visible():
                        continue
                    node.click(timeout=1200)
                    page.wait_for_timeout(300)
                    debug_info("DBG_POST_SEE_MORE", "Expanded post text using 'See more'.")
                except PlaywrightError:
                    continue

    def _extract_raw_post(self, page: Page, *, post_link: str, fallback_post_id: str) -> Dict[str, Any]:
        publish_raw = self._extract_publish_date_raw(page)
        publish_normalized = _normalize_publish_date_text(publish_raw)
        permalink = self._extract_permalink(page) or post_link
        post_id = _extract_post_id_from_link(permalink) or fallback_post_id or _extract_post_id_from_link(post_link)
        screenshot_path, screenshot_paths = self._capture_post_screenshot(page, permalink)
        return {
            "post_link": permalink,
            "post_id": post_id,
            "post_text": self._first_text(page, self._config.selectors_post_text),
            "publish_date_raw": publish_raw,
            "publish_date_normalized": publish_normalized,
            "images": self._extract_images(page),
            "post_screenshot_path": screenshot_path,
            "screenshot_paths": screenshot_paths,
        }

    def _extract_publish_date_raw(self, page: Page) -> str:
        for selector in self._config.selectors_post_publish:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue
            for node in nodes:
                candidate = _extract_publish_value_from_node(node)
                if candidate:
                    return candidate
        return self._extract_publish_date_fallback(page)

    def _extract_publish_date_fallback(self, page: Page) -> str:
        fallback_selectors = (
            "a[aria-label]",
            "span[aria-label]",
            "a[title]",
            "span[title]",
            "a[role='link']",
        )
        for selector in fallback_selectors:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue
            for node in nodes[:250]:
                for attr_name in ("aria-label", "title", "data-tooltip-content"):
                    candidate = _clean_candidate(_safe_get_attribute(node, attr_name))
                    if _looks_like_publish_date_hint(candidate):
                        return candidate
                candidate_text = _clean_candidate(_safe_inner_text(node))
                if _looks_like_publish_date_hint(candidate_text):
                    return candidate_text
        return ""

    def _extract_permalink(self, page: Page) -> str:
        for selector in self._config.selectors_post_permalink:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue
            for node in nodes[:10]:
                try:
                    href = (node.get_attribute("href") or "").strip()
                except PlaywrightError:
                    continue
                if not href:
                    continue
                resolved = href
                if href.startswith("/"):
                    resolved = f"https://www.facebook.com{href}"
                if "/posts/" in resolved or "/permalink/" in resolved:
                    return resolved
        return ""

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
                if not src.startswith("http"):
                    continue
                lowered = src.lower()
                if "static.xx.fbcdn.net" in lowered or "/emoji.php" in lowered or "/rsrc.php/" in lowered:
                    continue
                seen.add(src)
                urls.append(src)

        return urls

    def _capture_post_screenshot(self, page: Page, post_link: str) -> tuple[str, List[str]]:
        output_dir = Path(self._config.screenshots_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(post_link.encode("utf-8")).hexdigest()[:12]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        primary = output_dir / f"post_{stamp}_{digest}.png"
        fallback = output_dir / f"post_{stamp}_{digest}_fallback.png"

        try:
            container = self._locate_post_container(page)
            if container is not None:
                container.scroll_into_view_if_needed(timeout=1500)
                page.wait_for_timeout(250)
                container.screenshot(path=str(primary))
                debug_found("DBG_POST_SCREENSHOT_OK", f"Post element screenshot saved: {primary}")
                return str(primary), [str(primary)]
        except PlaywrightError as exc:
            debug_warning("DBG_POST_SCREENSHOT_ELEMENT_FAIL", f"Element screenshot failed, fallback to full-page: {exc}")

        try:
            page.screenshot(path=str(fallback), full_page=True)
            debug_found("DBG_POST_SCREENSHOT_OK", f"Fallback screenshot saved: {fallback}")
            return str(fallback), [str(fallback)]
        except PlaywrightError as exc:
            screenshot_error = make_app_error(
                code="ERR_POST_SCREENSHOT_CAPTURE_FAILED",
                technical_details=f"post_link={post_link} error={exc}",
            )
            debug_app_error(screenshot_error)
            return "", []

    def _locate_post_container(self, page: Page) -> Optional[ElementHandle]:
        for selector in self._config.selectors_post_container:
            try:
                node = page.query_selector(selector)
            except PlaywrightError:
                continue
            if node is not None:
                return node
        return None


def _normalize_publish_date_text(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .replace("\u200e", "")
        .replace("\u200f", "")
        .replace("\u202a", "")
        .replace("\u202b", "")
        .replace("\u202c", "")
        .strip()
    )


def _extract_publish_value_from_node(node: ElementHandle) -> str:
    href_candidate = _extract_iso_datetime_from_href(_safe_get_attribute(node, "href"))
    if href_candidate:
        return href_candidate

    for attr_name in ("datetime", "data-utime"):
        candidate = _extract_iso_datetime_from_timestamp(_safe_get_attribute(node, attr_name))
        if candidate:
            return candidate

    for attr_name in ("aria-label", "title"):
        candidate = _clean_candidate(_safe_get_attribute(node, attr_name))
        if candidate:
            return candidate

    for getter in (_safe_inner_text, _safe_text_content):
        candidate = _clean_candidate(getter(node))
        if candidate:
            return candidate

    return ""


def _extract_iso_datetime_from_href(href: str) -> str:
    cleaned = href.strip()
    if not cleaned:
        return ""

    try:
        parsed = urlparse(cleaned)
        query = parse_qs(parsed.query)
    except ValueError:
        return ""

    create_time_values = query.get("create_time", [])
    if not create_time_values:
        return ""

    return _extract_iso_datetime_from_timestamp(create_time_values[0])


def _extract_iso_datetime_from_timestamp(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or not cleaned.isdigit():
        return ""

    try:
        timestamp = int(cleaned)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (OverflowError, ValueError, OSError):
        return ""


def _extract_post_id_from_link(link: str) -> str:
    cleaned = str(link or "").strip()
    if not cleaned:
        return ""
    for marker in ("/posts/", "/permalink/"):
        if marker in cleaned:
            suffix = cleaned.split(marker, 1)[1]
            post_id = suffix.split("/", 1)[0].split("?", 1)[0]
            if post_id:
                return post_id
    return ""


def _safe_get_attribute(node: ElementHandle, name: str) -> str:
    try:
        return (node.get_attribute(name) or "").strip()
    except PlaywrightError:
        return ""


def _safe_inner_text(node: ElementHandle) -> str:
    try:
        return (node.inner_text() or "").strip()
    except PlaywrightError:
        return ""


def _safe_text_content(node: ElementHandle) -> str:
    try:
        return (node.text_content() or "").strip()
    except PlaywrightError:
        return ""


def _clean_candidate(value: str) -> str:
    return value.strip()


def _looks_like_publish_date_hint(value: str) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False

    if len(text) > 80:
        return False

    keyword_hints = (
        "hour",
        "hours",
        "hr",
        "hrs",
        "minute",
        "minutes",
        "min",
        "mins",
        "day",
        "days",
        "week",
        "weeks",
        "month",
        "months",
        "year",
        "years",
        "yesterday",
        "\u05e9\u05e2\u05d4",
        "\u05e9\u05e2\u05d5\u05ea",
        "\u05d3\u05e7\u05d4",
        "\u05d3\u05e7\u05d5\u05ea",
        "\u05d9\u05d5\u05dd",
        "\u05d9\u05de\u05d9\u05dd",
        "\u05e9\u05d1\u05d5\u05e2",
        "\u05d7\u05d5\u05d3\u05e9",
        "\u05e9\u05e0\u05d4",
        "\u05d0\u05ea\u05de\u05d5\u05dc",
        "\u05dc\u05e4\u05e0\u05d9",
    )
    if any(token in text for token in keyword_hints):
        return True

    if re.search(r"\b\d{1,2}[:.]\d{2}\b", text):
        return True
    if re.search(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b", text):
        return True
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", text):
        return True

    return False
