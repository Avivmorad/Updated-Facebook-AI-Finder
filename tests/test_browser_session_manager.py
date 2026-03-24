import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.scraper.browser_session_manager import BrowserSessionManager
from config.platform_access_config import PlatformAccessConfig


class _FakePage:
    def __init__(self) -> None:
        self.default_timeout = None
        self.default_navigation_timeout = None

    def set_default_timeout(self, value):
        self.default_timeout = value

    def set_default_navigation_timeout(self, value):
        self.default_navigation_timeout = value


class _FakeContext:
    def __init__(self, pages=None) -> None:
        self.pages = list(pages or [])
        self.closed = False

    def new_page(self):
        page = _FakePage()
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True


class _FakeChromium:
    def __init__(self, persistent_context) -> None:
        self.persistent_context = persistent_context
        self.persistent_calls = []

    def launch_persistent_context(self, user_data_dir, **kwargs):
        self.persistent_calls.append({"user_data_dir": user_data_dir, **kwargs})
        return self.persistent_context


class _FakePlaywright:
    def __init__(self, chromium) -> None:
        self.chromium = chromium
        self.stopped = False

    def start(self):
        return self

    def stop(self):
        self.stopped = True


class BrowserSessionManagerTests(unittest.TestCase):
    def test_open_requires_chrome_user_data_dir(self):
        manager = BrowserSessionManager(PlatformAccessConfig(chrome_user_data_dir="", chrome_profile_directory="Default"))

        with self.assertRaisesRegex(ValueError, "CHROME_USER_DATA_DIR"):
            manager.open()

    def test_open_requires_chrome_profile_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BrowserSessionManager(
                PlatformAccessConfig(chrome_user_data_dir=temp_dir, chrome_profile_directory="")
            )

            with self.assertRaisesRegex(ValueError, "CHROME_PROFILE_DIRECTORY"):
                manager.open()

    def test_open_requires_existing_profile_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BrowserSessionManager(
                PlatformAccessConfig(chrome_user_data_dir=temp_dir, chrome_profile_directory="Profile 7")
            )

            with self.assertRaisesRegex(ValueError, "Configured CHROME_PROFILE_DIRECTORY"):
                manager.open()

    def test_open_rejects_default_chrome_user_data_root(self):
        manager = BrowserSessionManager(
            PlatformAccessConfig(
                chrome_user_data_dir="C:/Users/Daniel/AppData/Local/Google/Chrome/User Data",
                chrome_profile_directory="Profile 5",
            )
        )

        with self.assertRaisesRegex(ValueError, "cannot be the default Chrome User Data root"):
            manager.open()

    def test_open_uses_chrome_persistent_context_with_profile_directory(self):
        first_page = _FakePage()
        persistent_context = _FakeContext(pages=[first_page])
        chromium = _FakeChromium(persistent_context=persistent_context)
        fake_playwright = _FakePlaywright(chromium)

        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "Default"
            profile_path.mkdir(parents=True, exist_ok=True)

            config = PlatformAccessConfig(
                chrome_user_data_dir=temp_dir,
                chrome_profile_directory="Default",
                headless=False,
                timeout_ms=3210,
            )

            with patch("app.scraper.browser_session_manager.sync_playwright", return_value=fake_playwright):
                manager = BrowserSessionManager(config).open()

            self.assertEqual(len(chromium.persistent_calls), 1)
            self.assertEqual(chromium.persistent_calls[0]["user_data_dir"], temp_dir)
            self.assertEqual(chromium.persistent_calls[0]["channel"], "chrome")
            self.assertFalse(chromium.persistent_calls[0]["headless"])
            self.assertIn("--profile-directory=Default", chromium.persistent_calls[0]["args"])
            self.assertIs(manager.page, first_page)
            self.assertEqual(first_page.default_timeout, 3210)
            self.assertEqual(first_page.default_navigation_timeout, 3210)

            manager.close()

        self.assertTrue(persistent_context.closed)
        self.assertTrue(fake_playwright.stopped)


if __name__ == "__main__":
    unittest.main()