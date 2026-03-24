from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    sync_playwright,
)

from app.utils.logger import get_logger, log_event
from config.platform_access_config import PlatformAccessConfig


logger = get_logger(__name__)


class BrowserSessionManager:
    def __init__(self, config: PlatformAccessConfig) -> None:
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
        self._playwright = sync_playwright().start()

        log_event(
            logger,
            20,
            "browser_session_opening",
            browser_channel="chrome",
            headless=self._config.headless,
            chrome_profile_directory=profile_directory.name,
            chrome_user_data_dir=user_data_dir,
        )

        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                **self._launch_kwargs(),
            )
            log_event(logger, 20, "browser_context_created", pages_count=len(self._context.pages))
            pages = self._context.pages
            if pages:
                self._page = pages[0]
                log_event(logger, 20, "browser_page_selected", source="existing", page_url=self._safe_page_url(self._page))
            else:
                self._page = self._context.new_page()
                log_event(logger, 20, "browser_page_selected", source="new", page_url=self._safe_page_url(self._page))
        except Exception as exc:
            self.close()
            err_msg = str(exc)
            if "exitCode=21" in err_msg or "Target page, context or browser has been closed" in err_msg:
                raise RuntimeError(
                    "Chrome profile is locked by another Chrome instance. "
                    "Close ALL Chrome windows (including system tray) and try again."
                ) from exc
            raise

        self._page.set_default_timeout(self._config.timeout_ms)
        self._page.set_default_navigation_timeout(self._config.timeout_ms)
        log_event(logger, 20, "browser_session_opened", timeout_ms=self._config.timeout_ms)
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
            raise ValueError("CHROME_USER_DATA_DIR is required for the Facebook Chrome profile session")

        user_data_dir = Path(configured).expanduser()
        if not user_data_dir.exists():
            raise ValueError(f"Configured CHROME_USER_DATA_DIR does not exist: {user_data_dir}")

        return user_data_dir

    def _ensure_supported_user_data_dir(self, user_data_dir: Path) -> None:
        normalized = str(user_data_dir).replace("\\", "/").strip().lower().rstrip("/")
        if normalized.endswith("/google/chrome/user data"):
            raise ValueError(
                "CHROME_USER_DATA_DIR cannot be the default Chrome User Data root for Playwright automation. "
                "Set CHROME_USER_DATA_DIR to a dedicated copied profile root (for example: "
                "C:/Users/Daniel/OneDrive/Desktop/AgentsTests/Facebook-AI-Finder/data/chrome-user-data)."
            )

    def _check_profile_not_locked(self, user_data_dir: Path) -> None:
        lock_file = user_data_dir / "SingletonLock"
        lock_file_win = user_data_dir / "lockfile"
        if lock_file.exists() or lock_file_win.exists():
            raise RuntimeError(
                "Chrome is currently running and locking the profile directory. "
                "Close ALL Chrome windows (check system tray near the clock too) and try again. "
                f"Lock detected in: {user_data_dir}"
            )

    def _require_profile_directory(self, user_data_dir: Path) -> Path:
        configured = self._config.chrome_profile_directory.strip()
        if not configured:
            raise ValueError("CHROME_PROFILE_DIRECTORY is required for the Facebook Chrome profile session")

        profile_directory = user_data_dir / configured
        if not profile_directory.exists():
            raise ValueError(
                "Configured CHROME_PROFILE_DIRECTORY was not found inside CHROME_USER_DATA_DIR: "
                f"{profile_directory}"
            )

        return profile_directory

    def _safe_page_url(self, page: Optional[Page]) -> str:
        if page is None:
            return ""
        return str(getattr(page, "url", "") or "").strip()

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

    def __enter__(self) -> "BrowserSessionManager":
        return self.open()

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()
