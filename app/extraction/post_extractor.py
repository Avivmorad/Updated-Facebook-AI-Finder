from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

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
        permalink = self._extract_permalink(page, fallback_link=post_link) or post_link
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

    def _extract_permalink(self, page: Page, *, fallback_link: str = "") -> str:
        candidates: List[Dict[str, Any]] = []
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
                normalized = _normalize_post_permalink_href(href)
                if not normalized:
                    continue
                candidates.append(_build_permalink_candidate(node=node, normalized_href=normalized, selector=selector))

        best = _select_best_permalink_candidate(candidates)
        if best is not None:
            return str(best.get("href") or "").strip()
        return _normalize_post_permalink_href(fallback_link)

    def _first_text(self, page: Page, selectors: List[str]) -> str:
        candidates: List[Dict[str, Any]] = []
        for selector in selectors:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue
            for node in nodes[:20]:
                candidate = _build_text_candidate(node=node, selector=selector)
                if candidate is not None:
                    candidates.append(candidate)

        best = _select_best_text_candidate(candidates)
        if best is None:
            return ""
        return str(best.get("text") or "").strip()

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
        candidates: List[Dict[str, Any]] = []
        seen_signatures: Set[str] = set()
        for selector in self._config.selectors_post_container:
            try:
                nodes = page.query_selector_all(selector)
            except PlaywrightError:
                continue
            for node in nodes[:20]:
                candidate = _build_container_candidate(node=node, selector=selector)
                if candidate is None:
                    continue
                signature = str(candidate.get("signature") or "")
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                candidates.append(candidate)

        best = _select_best_container_candidate(candidates)
        if best is not None:
            return best.get("node")
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


def _normalize_post_permalink_href(href: str) -> str:
    cleaned = str(href or "").strip()
    if not cleaned:
        return ""

    resolved = cleaned
    if cleaned.startswith("/"):
        resolved = f"https://www.facebook.com{cleaned}"
    if not resolved.startswith("http"):
        return ""

    try:
        parsed = urlparse(resolved)
    except ValueError:
        return ""

    host = parsed.netloc.lower()
    if host and "facebook.com" not in host and "fb.com" not in host:
        return ""

    path = parsed.path.lower()
    query = parse_qs(parsed.query)
    if "/photo" in path or path.endswith("photo.php") or "set" in query:
        return ""
    if "/posts/" not in path and "/permalink/" not in path and "story_fbid" not in query and "fbid" not in query:
        return ""

    kept_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.startswith("__"):
            continue
        if key in {"comment_id", "reply_comment_id", "notif_id", "notif_t", "ref", "acontext"}:
            continue
        kept_items.append((key, value))

    if "/groups/" in path and "/posts/" in path:
        kept_items = [(key, value) for (key, value) in kept_items if key not in {"story_fbid", "id"}]

    query_text = urlencode(kept_items, doseq=True)
    return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, parsed.params, query_text, ""))


def _looks_like_permalink_text(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if _looks_like_publish_date_hint(text):
        return True
    markers = ("comment", "תגובה", "share", "שיתוף", "like", "לייק")
    return any(marker in lowered for marker in markers)


def _safe_box(node: ElementHandle) -> Dict[str, float]:
    try:
        box = node.bounding_box()
    except PlaywrightError:
        box = None
    if not box:
        return {"width": 0.0, "height": 0.0}
    return {
        "width": float(box.get("width", 0.0) or 0.0),
        "height": float(box.get("height", 0.0) or 0.0),
    }


def _safe_visible(node: ElementHandle) -> bool:
    try:
        return bool(node.is_visible())
    except PlaywrightError:
        return False


def _safe_label_text(node: ElementHandle) -> str:
    parts = [
        _safe_inner_text(node),
        _safe_get_attribute(node, "aria-label"),
        _safe_get_attribute(node, "title"),
    ]
    return " ".join(part for part in parts if part).strip()


def _build_text_candidate(node: ElementHandle, selector: str) -> Optional[Dict[str, Any]]:
    text = _safe_inner_text(node).strip()
    if not text:
        return None

    box = _safe_box(node)
    visible = _safe_visible(node)
    return {
        "node": node,
        "selector": selector,
        "text": text,
        "text_length": len(text),
        "visible": visible,
        "width": box["width"],
        "height": box["height"],
    }


def _build_permalink_candidate(node: ElementHandle, normalized_href: str, selector: str) -> Dict[str, Any]:
    box = _safe_box(node)
    label = _safe_label_text(node)
    return {
        "node": node,
        "selector": selector,
        "href": normalized_href,
        "visible": _safe_visible(node),
        "width": box["width"],
        "height": box["height"],
        "label_length": len(label),
        "label_text": label,
    }


def _build_container_candidate(node: ElementHandle, selector: str) -> Optional[Dict[str, Any]]:
    box = _safe_box(node)
    if box["width"] < 240 or box["height"] < 180:
        return None

    try:
        metrics = node.evaluate(
            """
            (element) => {
              const text = (element.innerText || "").trim();
              const links = Array.from(element.querySelectorAll("a[href]"));
              const images = Array.from(element.querySelectorAll("img[src^='http']"));
              const actions = Array.from(element.querySelectorAll("div[role='button'], button"));
              const role = element.getAttribute("role") || "";
              const articleDescendantCount = element.querySelectorAll("div[role='article']").length;
              const actionText = actions.map((item) => (item.innerText || "").trim()).join(" | ");
              const permalinkCount = links.filter((item) => {
                const href = item.getAttribute("href") || "";
                return href.includes("/posts/") || href.includes("/permalink/") || href.includes("story_fbid=");
              }).length;
              const photoLinkCount = links.filter((item) => {
                const href = item.getAttribute("href") || "";
                return href.includes("/photo") || href.includes("photo.php") || href.includes("set=");
              }).length;
              return {
                textLength: text.length,
                permalinkCount,
                photoLinkCount,
                imageCount: images.length,
                actionCount: actions.length,
                articleDescendantCount,
                actionText,
                role,
                signature: `${element.tagName}|${role}|${text.slice(0, 120)}`,
              };
            }
            """
        )
    except PlaywrightError:
        return None

    return {
        "node": node,
        "selector": selector,
        "visible": _safe_visible(node),
        "width": box["width"],
        "height": box["height"],
        "text_length": int(metrics.get("textLength", 0) or 0),
        "permalink_count": int(metrics.get("permalinkCount", 0) or 0),
        "photo_link_count": int(metrics.get("photoLinkCount", 0) or 0),
        "image_count": int(metrics.get("imageCount", 0) or 0),
        "action_count": int(metrics.get("actionCount", 0) or 0),
        "article_descendant_count": int(metrics.get("articleDescendantCount", 0) or 0),
        "action_text": str(metrics.get("actionText", "") or ""),
        "role": str(metrics.get("role", "") or ""),
        "signature": str(metrics.get("signature", "") or ""),
    }


def _select_best_text_candidate(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_score = float("-inf")

    for candidate in candidates:
        text = str(candidate.get("text") or "").strip()
        if len(text) < 8:
            continue

        width = float(candidate.get("width", 0.0) or 0.0)
        height = float(candidate.get("height", 0.0) or 0.0)
        visible = bool(candidate.get("visible"))
        selector = str(candidate.get("selector") or "")

        score = 0.0
        if visible:
            score += 400.0
        score += min(len(text) * 2.0, 700.0)
        score += min((width * height) / 150.0, 500.0)
        if width < 80 or height < 18:
            score -= 500.0
        if _looks_like_publish_date_hint(text):
            score -= 450.0
        if "data-ad-preview='message'" in selector:
            score += 180.0
        if "div[role='article']" in selector:
            score += 80.0

        if score > best_score:
            best_score = score
            best = candidate

    return best


def _select_best_permalink_candidate(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_score = float("-inf")

    for candidate in candidates:
        href = str(candidate.get("href") or "").strip()
        if not href:
            continue

        width = float(candidate.get("width", 0.0) or 0.0)
        height = float(candidate.get("height", 0.0) or 0.0)
        visible = bool(candidate.get("visible"))
        selector = str(candidate.get("selector") or "")
        label_text = str(candidate.get("label_text") or "")

        score = 0.0
        if visible:
            score += 250.0
        score += min(width * height, 10000.0) / 50.0
        score += min(float(candidate.get("label_length", 0) or 0) * 6.0, 180.0)
        if width < 24 or height < 12:
            score -= 320.0
        if _looks_like_publish_date_hint(label_text):
            score += 180.0
        elif _looks_like_permalink_text(label_text):
            score += 80.0
        if "/groups/" in href and "/posts/" in href:
            score += 250.0
        elif "/permalink/" in href:
            score += 220.0
        elif "story_fbid=" in href:
            score += 180.0
        elif "fbid=" in href:
            score += 100.0
        if "a[href*='/posts/']" in selector:
            score += 60.0

        if score > best_score:
            best_score = score
            best = candidate

    return best


def _select_best_container_candidate(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_score = float("-inf")

    for candidate in candidates:
        width = float(candidate.get("width", 0.0) or 0.0)
        height = float(candidate.get("height", 0.0) or 0.0)
        visible = bool(candidate.get("visible"))
        selector = str(candidate.get("selector") or "")
        role = str(candidate.get("role") or "")
        text_length = int(candidate.get("text_length", 0) or 0)
        permalink_count = int(candidate.get("permalink_count", 0) or 0)
        photo_link_count = int(candidate.get("photo_link_count", 0) or 0)
        image_count = int(candidate.get("image_count", 0) or 0)
        action_count = int(candidate.get("action_count", 0) or 0)
        article_descendant_count = int(candidate.get("article_descendant_count", 0) or 0)
        action_text = str(candidate.get("action_text") or "")

        score = 0.0
        if visible:
            score += 500.0
        score += min(width * height, 600000.0) / 900.0
        score += min(text_length, 1000)
        score += min(permalink_count * 180.0, 540.0)
        score += min(image_count * 110.0, 330.0)
        score += min(action_count * 20.0, 120.0)
        score -= min(photo_link_count * 90.0, 360.0)
        if any(label in action_text for label in ("Like", "Comment", "Share", "לייק", "תגובה", "שיתוף")):
            score += 180.0
        if article_descendant_count > 0:
            score -= min(article_descendant_count * 900.0, 2700.0)
        if selector == "div[role='main']" or role == "main":
            score -= 2200.0
        if selector == "div[role='article']":
            score += 520.0
        if width * height > 1800000.0:
            score -= 1200.0
        if width < 320 or height < 220:
            score -= 500.0

        if score > best_score:
            best_score = score
            best = candidate

    return best


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
