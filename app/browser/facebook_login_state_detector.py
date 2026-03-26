from dataclasses import dataclass
from typing import Optional, Set

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)

_LOGIN_URL_MARKERS = ("/login", "login.php")
_CHECKPOINT_URL_MARKERS = ("/checkpoint", "/recover/code", "/security/")
_LOGIN_FORM_SELECTORS = (
    "input[name='email']",
    "input[name='pass']",
    "button[name='login']",
    "#loginbutton",
)


@dataclass(frozen=True)
class FacebookLoginCheckResult:
    is_logged_in: bool
    state: str
    reason: str
    url: str


class FacebookLoginStateDetector:
    def detect_login_state(self, page: Page) -> FacebookLoginCheckResult:
        url = self._safe_url(page)
        url_lower = url.lower()
        title = self._safe_title(page).lower()
        body_text = self._safe_body_text(page).lower()
        cookie_names = self._cookie_names(page)
        has_auth_cookies = {"c_user", "xs"}.issubset(cookie_names)

        if self._looks_like_checkpoint(url_lower, title, body_text):
            result = FacebookLoginCheckResult(False, "checkpoint", "facebook_checkpoint_detected", url)
        elif self._looks_like_login_page(page, url_lower, title, body_text):
            result = FacebookLoginCheckResult(False, "login_page", "facebook_login_page_detected", url)
        elif self._looks_blank(url_lower, title, body_text):
            result = FacebookLoginCheckResult(False, "blank_page", "facebook_blank_page_detected", url)
        elif has_auth_cookies:
            result = FacebookLoginCheckResult(True, "logged_in", "facebook_authenticated_session_detected", url)
        else:
            result = FacebookLoginCheckResult(False, "unknown", "facebook_authenticated_session_not_detected", url)

        log_event(logger, 20 if result.is_logged_in else 30, "facebook_login_state_detected", state=result.state, reason=result.reason, url=result.url)
        return result

    def is_logged_in_to_facebook(self, page: Page) -> bool:
        return self.detect_login_state(page).is_logged_in

    def _safe_url(self, page: Page) -> str:
        return str(getattr(page, "url", "") or "").strip()

    def _safe_title(self, page: Page) -> str:
        try:
            return (page.title() or "").strip()
        except PlaywrightError:
            return ""

    def _safe_body_text(self, page: Page) -> str:
        try:
            body = page.query_selector("body")
        except PlaywrightError:
            return ""

        if body is None:
            return ""

        try:
            return (body.inner_text() or "").strip()
        except PlaywrightError:
            return ""

    def _cookie_names(self, page: Page) -> Set[str]:
        try:
            cookies = page.context.cookies()
        except PlaywrightError:
            return set()
        return {str(item.get("name", "")).strip() for item in cookies}

    def _looks_like_checkpoint(self, url: str, title: str, body_text: str) -> bool:
        return any(marker in url for marker in _CHECKPOINT_URL_MARKERS) or "checkpoint" in title or "checkpoint" in body_text

    def _looks_like_login_page(self, page: Page, url: str, title: str, body_text: str) -> bool:
        if any(marker in url for marker in _LOGIN_URL_MARKERS):
            return True
        if "log in" in title or "login" in title:
            return True
        if "log in to facebook" in body_text or "facebook helps you connect" in body_text:
            return True

        for selector in _LOGIN_FORM_SELECTORS:
            try:
                if page.query_selector(selector) is not None:
                    return True
            except PlaywrightError:
                continue

        return False

    def _looks_blank(self, url: str, title: str, body_text: str) -> bool:
        if url == "about:blank":
            return True
        return not title and not body_text


def is_logged_in_to_facebook(page: Page) -> bool:
    return FacebookLoginStateDetector().is_logged_in_to_facebook(page)