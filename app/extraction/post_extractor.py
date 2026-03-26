from datetime import datetime, timezone
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
        debug_step("DBG_POST_OPEN", "פותח את עמוד הפוסט כדי לחלץ טקסט, תמונות ותאריך פרסום.")

        for attempt in range(1, attempts + 1):
            try:
                with self._facebook_access.authenticated_session() as session:
                    page = session.page
                    debug_info("DBG_POST_OPEN_ATTEMPT", f"ניסיון חילוץ פוסט {attempt}/{attempts}: {post_link}")
                    self._open_post_page(page, post_link)
                    raw = self._extract_raw_post(page, post_link)
                    result.raw_post_data = raw
                    result.normalized_post_data = normalize_post_data(raw)
                    if attempt > 1:
                        result.warnings.append(f"post_extraction_retry_success:{attempt}")
                    if result.normalized_post_data.get("post_text"):
                        debug_found("DBG_POST_TEXT_OK", "נמצא טקסט לפוסט.")
                    else:
                        missing_text = make_app_error(code="ERR_POST_TEXT_NOT_FOUND")
                        result.warnings.append(missing_text.code)
                        debug_missing(missing_text.code, missing_text.summary_he)

                    image_count = len(result.normalized_post_data.get("images", []))
                    if image_count > 0:
                        debug_found("DBG_POST_IMAGES_OK", f"נמצאו {image_count} תמונות.")
                    else:
                        missing_images = make_app_error(code="ERR_POST_IMAGES_NOT_FOUND")
                        result.warnings.append(missing_images.code)
                        debug_missing(missing_images.code, missing_images.summary_he)

                    if result.normalized_post_data.get("publish_date"):
                        debug_found("DBG_POST_DATE_OK", "נמצא תאריך פרסום לפוסט.")
                    else:
                        missing_date = make_app_error(code="ERR_POST_PUBLISH_DATE_MISSING")
                        result.warnings.append(missing_date.code)
                        debug_missing(missing_date.code, missing_date.summary_he)

                    debug_found("DBG_POST_EXTRACT_OK", "חילוץ הפוסט הושלם בהצלחה.")
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
                    default_summary_he="טעינת עמוד הפוסט נכשלה",
                    default_cause_he="אירעה שגיאה בזמן ניווט/טעינה של עמוד הפוסט",
                    default_action_he="נסה שוב, ואם חוזר בדוק שהקישור תקין ונגיש",
                )
                result.warnings.append(f"extraction_attempt_{attempt}_failed")
                logger.warning("Post extraction attempt %s/%s failed for %s: %s", attempt, attempts, post_link, str(last_error))
                debug_app_error(last_error)
                debug_warning("DBG_POST_EXTRACT_RETRY", f"חילוץ הפוסט נכשל בניסיון {attempt}/{attempts}.")

        result.success = False
        result.error = last_error.code
        debug_app_error(last_error)
        return result

    def _open_post_page(self, page: Page, post_link: str) -> None:
        response = page.goto(post_link, wait_until="commit", timeout=self._config.timeout_ms)
        if response is not None and not response.ok:
            raise make_app_error(
                code="ERR_POST_PAGE_LOAD_FAILED",
                technical_details=f"post_link={post_link} status={response.status}",
            )
        if str(getattr(page, "url", "") or "").strip() == "about:blank":
            raise make_app_error(
                code="ERR_POST_PAGE_LOAD_FAILED",
                technical_details=f"post_link={post_link} ended_on=about:blank",
            )

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
            "publish_date": self._extract_publish_date(page),
            "images": self._extract_images(page),
        }

    def _extract_publish_date(self, page: Page) -> str:
        for selector in self._config.selectors_post_publish:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue

            for node in nodes:
                candidate = _extract_publish_value_from_node(node)
                if candidate:
                    return candidate

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
                seen.add(src)
                urls.append(src)

        return urls


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
