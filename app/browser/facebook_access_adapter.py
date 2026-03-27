from contextlib import contextmanager
from typing import Iterator, Optional

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from app.browser.browser_session_manager import BrowserSessionManager
from app.browser.facebook_login_state_detector import FacebookLoginCheckResult, FacebookLoginStateDetector
from app.browser.step_debug import capture_browser_step
from app.config.browser import BrowserConfig
from app.utils.app_errors import AppError, make_app_error
from app.utils.debugging import debug_found, debug_step
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class FacebookAuthenticationRequiredError(RuntimeError):
    def __init__(self, app_error: AppError) -> None:
        self.app_error = app_error
        super().__init__(app_error.summary_he)


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
        debug_step("DBG_FACEBOOK_HOME", "Opening Facebook home page.")
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
            raise make_app_error(
                code="ERR_FACEBOOK_HOME_OPEN_FAILED",
                technical_details=str(exc),
            ) from exc

        if response is not None and not response.ok:
            raise make_app_error(
                code="ERR_FACEBOOK_HOME_OPEN_FAILED",
                technical_details=f"status={response.status}",
            )

        final_url = str(getattr(page, "url", "") or "").strip()
        log_event(
            logger,
            20,
            "facebook_navigation_completed",
            final_url=final_url,
            http_status=response.status if response is not None else "none",
        )
        if final_url == "about:blank":
            raise make_app_error(
                code="ERR_FACEBOOK_HOME_OPEN_FAILED",
                technical_details="facebook_navigation_ended_on_about_blank",
            )
        page.wait_for_timeout(1200)
        debug_found("DBG_FACEBOOK_HOME_OK", "Facebook home page opened successfully.")
        capture_browser_step(
            self._config,
            page=page,
            step_code="FACEBOOK_HOME_OPENED",
            message="Facebook home page opened successfully",
            context="facebook_access",
        )

    def ensure_logged_in(self, page: Page) -> None:
        result = self.get_login_check_result(page)
        if result.is_logged_in:
            debug_found("DBG_FACEBOOK_LOGIN_OK", "Facebook login is active in the selected profile.")
            capture_browser_step(
                self._config,
                page=page,
                step_code="FACEBOOK_LOGIN_OK",
                message="Facebook authenticated session detected",
                context="facebook_access",
            )
            return
        capture_browser_step(
            self._config,
            page=page,
            step_code="FACEBOOK_LOGIN_MISSING",
            message=f"Facebook authentication missing (state={result.state})",
            context="facebook_access",
        )
        raise FacebookAuthenticationRequiredError(
            app_error=make_app_error(
                code="ERR_FACEBOOK_NOT_LOGGED_IN",
                technical_details=f"detected_state={result.state} url={result.url}",
            ),
        )

    def get_login_check_result(self, page: Page) -> FacebookLoginCheckResult:
        return self._login_state_detector.detect_login_state(page)

    def is_logged_in_to_facebook(self, page: Page) -> bool:
        return self._login_state_detector.is_logged_in_to_facebook(page)

    def navigate(self, page: Page, url: str) -> None:
        debug_step("DBG_FACEBOOK_NAVIGATE", f"Navigating to URL: {url}")
        current_url = str(getattr(page, "url", "") or "").strip()
        log_event(logger, 20, "facebook_navigation_requested", current_url=current_url, target_url=url)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=self._config.timeout_ms)
        except PlaywrightError as exc:
            raise make_app_error(
                code="ERR_GROUPS_FEED_OPEN_FAILED" if "/groups/feed" in url else "ERR_FACEBOOK_HOME_OPEN_FAILED",
                technical_details=f"url={url} error={exc}",
            ) from exc

        if response is not None and not response.ok:
            raise make_app_error(
                code="ERR_GROUPS_FEED_OPEN_FAILED" if "/groups/feed" in url else "ERR_FACEBOOK_HOME_OPEN_FAILED",
                technical_details=f"url={url} status={response.status}",
            )

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
            raise make_app_error(
                code="ERR_GROUPS_FEED_OPEN_FAILED" if "/groups/feed" in url else "ERR_FACEBOOK_HOME_OPEN_FAILED",
                technical_details=f"url={url} ended_on=about:blank",
            )
        debug_found("DBG_FACEBOOK_NAVIGATE_OK", f"Navigation completed: {url}")
        capture_browser_step(
            self._config,
            page=page,
            step_code="FACEBOOK_NAVIGATE_OK",
            message=f"Navigation completed: {url}",
            context="facebook_access",
        )
