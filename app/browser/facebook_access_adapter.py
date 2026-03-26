from contextlib import contextmanager
from typing import Iterator, Optional

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from app.browser.browser_session_manager import BrowserSessionManager
from app.browser.facebook_login_state_detector import FacebookLoginCheckResult, FacebookLoginStateDetector
from app.config.browser import BrowserConfig
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class FacebookAuthenticationRequiredError(RuntimeError):
    pass


class FacebookAccessAdapter:
    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        login_state_detector: Optional[FacebookLoginStateDetector] = None,
    ) -> None:
        self._config = config or BrowserConfig()
        self._login_state_detector = login_state_detector or FacebookLoginStateDetector()

    @contextmanager
    def authenticated_session(self) -> Iterator[BrowserSessionManager]:
        session = BrowserSessionManager(self._config).open()
        try:
            page = session.page
            self.open_facebook(page)
            self.ensure_logged_in(page)
            yield session
        finally:
            session.close()

    def open_facebook(self, page: Page) -> None:
        current_url = str(getattr(page, "url", "") or "").strip()
        log_event(
            logger,
            20,
            "facebook_navigation_requested",
            current_url=current_url,
            target_url=self._config.facebook_home_url,
        )
        try:
            response = page.goto(
                self._config.facebook_home_url,
                wait_until="domcontentloaded",
                timeout=self._config.timeout_ms,
            )
        except PlaywrightError as exc:
            raise RuntimeError(f"facebook home navigation failed: {str(exc)}") from exc

        if response is not None and not response.ok:
            raise RuntimeError(f"facebook page load failed with status {response.status}")

        final_url = str(getattr(page, "url", "") or "").strip()
        log_event(
            logger,
            20,
            "facebook_navigation_completed",
            final_url=final_url,
            http_status=response.status if response is not None else "none",
        )
        if final_url == "about:blank":
            raise RuntimeError(
                "facebook home navigation ended on about:blank. "
                "Check CHROME_USER_DATA_DIR / CHROME_PROFILE_DIRECTORY and Chrome profile compatibility."
            )
        page.wait_for_timeout(1200)

    def ensure_logged_in(self, page: Page) -> None:
        result = self.get_login_check_result(page)
        if result.is_logged_in:
            return
        raise FacebookAuthenticationRequiredError(
            "Facebook is not logged in in the configured Chrome profile. "
            "Sign in manually in that Chrome profile and rerun. No automatic login is performed. "
            f"Detected state: {result.state}."
        )

    def get_login_check_result(self, page: Page) -> FacebookLoginCheckResult:
        return self._login_state_detector.detect_login_state(page)

    def is_logged_in_to_facebook(self, page: Page) -> bool:
        return self._login_state_detector.is_logged_in_to_facebook(page)

    def navigate(self, page: Page, url: str) -> None:
        current_url = str(getattr(page, "url", "") or "").strip()
        log_event(logger, 20, "facebook_navigation_requested", current_url=current_url, target_url=url)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=self._config.timeout_ms)
        except PlaywrightError as exc:
            raise RuntimeError(f"facebook navigation failed for {url}: {str(exc)}") from exc

        if response is not None and not response.ok:
            raise RuntimeError(f"facebook navigation failed with status {response.status} for {url}")

        final_url = str(getattr(page, "url", "") or "").strip()
        log_event(
            logger,
            20,
            "facebook_navigation_completed",
            final_url=final_url,
            http_status=response.status if response is not None else "none",
            target_url=url,
        )
        if final_url == "about:blank":
            raise RuntimeError(f"facebook navigation ended on about:blank for {url}")
