from pathlib import Path
from time import sleep
from typing import Optional

from playwright.sync_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    sync_playwright,
)

from app.config.browser import BrowserConfig
from app.utils.app_errors import make_app_error
from app.utils.debugging import debug_found, debug_info, debug_step, debug_warning
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class BrowserSessionManager:
    def __init__(self, config: BrowserConfig) -> None:
        self._config = config
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser page is not initialized")
        return self._page

    def open(self) -> "BrowserSessionManager":
        user_data_dir = self._require_user_data_dir()
        profile_directory = self._require_profile_directory(user_data_dir)
        self._ensure_supported_user_data_dir(user_data_dir)
        self._check_profile_not_locked(user_data_dir)
        attempts = max(1, self._config.retries + 1)

        debug_step("DBG_BROWSER_OPEN", "פותח את Google Chrome עם הפרופיל השמור.")
        debug_info(
            "DBG_BROWSER_PROFILE",
            f"CHROME_USER_DATA_DIR={user_data_dir} | CHROME_PROFILE_DIRECTORY={profile_directory.name}",
        )

        log_event(
            logger,
            20,
            "browser_session_opening",
            browser_channel="chrome",
            headless=self._config.headless,
            chrome_profile_directory=profile_directory.name,
            chrome_user_data_dir=user_data_dir,
            attempts=attempts,
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            self._playwright = sync_playwright().start()
            try:
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    **self._launch_kwargs(),
                )
                debug_found("DBG_BROWSER_CONTEXT_OK", f"Chrome נפתח בהצלחה (ניסיון {attempt}/{attempts}).")
                log_event(logger, 20, "browser_context_created", pages_count=len(self._context.pages), attempt=attempt)
                pages = self._context.pages
                if pages:
                    self._page = pages[0]
                    log_event(
                        logger,
                        20,
                        "browser_page_selected",
                        source="existing",
                        page_url=self._safe_page_url(self._page),
                        attempt=attempt,
                    )
                else:
                    self._page = self._context.new_page()
                    log_event(
                        logger,
                        20,
                        "browser_page_selected",
                        source="new",
                        page_url=self._safe_page_url(self._page),
                        attempt=attempt,
                    )
                break
            except Exception as exc:
                last_error = exc
                err_msg = str(exc)
                self.close()

                if self._is_locked_profile_error(user_data_dir, err_msg):
                    raise make_app_error(
                        code="ERR_BROWSER_PROFILE_LOCKED",
                        technical_details=err_msg,
                    ) from exc

                if attempt >= attempts or not self._is_retryable_launch_error(err_msg):
                    raise make_app_error(
                        code="ERR_BROWSER_PROFILE_INCOMPATIBLE",
                        technical_details=self._build_profile_startup_error_message(err_msg),
                    ) from exc

                debug_warning(
                    "DBG_BROWSER_RETRY",
                    f"פתיחת Chrome נכשלה בניסיון {attempt}/{attempts}. מנסה שוב.",
                )
                sleep(min(1.5, 0.3 * attempt))
        else:
            raise make_app_error(
                code="ERR_BROWSER_PROFILE_INCOMPATIBLE",
                technical_details=str(last_error),
            ) from last_error

        self._page.set_default_timeout(self._config.timeout_ms)
        self._page.set_default_navigation_timeout(self._config.timeout_ms)
        log_event(logger, 20, "browser_session_opened", timeout_ms=self._config.timeout_ms)
        debug_found("DBG_BROWSER_READY", "Google Chrome מוכן להמשך ניווט.")
        return self

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("Browser context is not initialized")
        return self._context

    def _launch_kwargs(self) -> dict:
        return {
            "channel": "chrome",
            "headless": self._config.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                f"--profile-directory={self._config.chrome_profile_directory}",
            ],
        }

    def _require_user_data_dir(self) -> Path:
        configured = self._config.chrome_user_data_dir.strip()
        if not configured:
            raise make_app_error(
                code="ERR_BROWSER_USER_DATA_DIR_MISSING",
                technical_details="CHROME_USER_DATA_DIR is empty",
            )

        user_data_dir = Path(configured).expanduser()
        if not user_data_dir.exists():
            raise make_app_error(
                code="ERR_BROWSER_USER_DATA_DIR_MISSING",
                technical_details=f"path_not_found={user_data_dir}",
            )

        return user_data_dir

    def _ensure_supported_user_data_dir(self, user_data_dir: Path) -> None:
        normalized = str(user_data_dir).replace("\\", "/").strip().lower().rstrip("/")
        if normalized.endswith("/google/chrome/user data"):
            raise make_app_error(
                code="ERR_BROWSER_PROFILE_INCOMPATIBLE",
                summary_he="CHROME_USER_DATA_DIR מצביע על תיקיית ברירת המחדל של Chrome",
                cause_he="Playwright לא תומך בשימוש ישיר בתיקיית User Data הראשית של Chrome",
                action_he="השתמש בתיקיית פרופיל מועתקת ייעודית לפרויקט",
                technical_details=f"user_data_dir={user_data_dir}",
            )

    def _check_profile_not_locked(self, user_data_dir: Path) -> None:
        lock_file = user_data_dir / "SingletonLock"
        lock_file_win = user_data_dir / "lockfile"
        if lock_file.exists() or lock_file_win.exists():
            raise make_app_error(
                code="ERR_BROWSER_PROFILE_LOCKED",
                technical_details=f"lock_detected_in={user_data_dir}",
            )

    def _require_profile_directory(self, user_data_dir: Path) -> Path:
        configured = self._config.chrome_profile_directory.strip()
        if not configured:
            raise make_app_error(
                code="ERR_BROWSER_PROFILE_DIR_MISSING",
                technical_details="CHROME_PROFILE_DIRECTORY is empty",
            )

        profile_directory = user_data_dir / configured
        if not profile_directory.exists():
            raise make_app_error(
                code="ERR_BROWSER_PROFILE_DIR_MISSING",
                technical_details=f"profile_not_found={profile_directory}",
            )

        return profile_directory

    def _safe_page_url(self, page: Optional[Page]) -> str:
        if page is None:
            return ""
        return str(getattr(page, "url", "") or "").strip()

    def _is_locked_profile_error(self, user_data_dir: Path, err_msg: str) -> bool:
        lock_file = user_data_dir / "SingletonLock"
        lock_file_win = user_data_dir / "lockfile"
        if lock_file.exists() or lock_file_win.exists():
            return True
        return "exitCode=21" in err_msg

    def _is_retryable_launch_error(self, err_msg: str) -> bool:
        retryable_markers = (
            "Browser.getWindowForTarget",
            "Target page, context or browser has been closed",
            "Target closed",
        )
        return any(marker in err_msg for marker in retryable_markers)

    def _build_profile_startup_error_message(self, err_msg: str) -> str:
        return (
            "Chrome could not open the configured copied profile. "
            "This usually means the copied profile is incompatible, incomplete, or contains data "
            "Chrome cannot use in this automation session. Close all Chrome windows and, if needed, "
            "recreate the copied profile and sign in again manually. "
            f"Details: {err_msg}"
        )

    def close(self) -> None:
        if self._context is not None:
            try:
                self._context.close()
            except PlaywrightError:
                # Ignore close failures when context/browser was already closed upstream.
                pass
            self._context = None

        if self._playwright is not None:
            try:
                self._playwright.stop()
            except PlaywrightError:
                pass
            self._playwright = None

        self._page = None
        log_event(logger, 20, "browser_session_closed")
        debug_info("DBG_BROWSER_CLOSED", "סוגר את סשן הדפדפן הנוכחי.")

    def __enter__(self) -> "BrowserSessionManager":
        return self.open()

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()
