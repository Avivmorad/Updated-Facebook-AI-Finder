import logging

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


USER_DATA_DIR = r"C:\Users\Daniel\AppData\Local\Google\Chrome\User Data"
PROFILE_DIRECTORY = "Profile 5"
TARGET_URL = "https://www.facebook.com/marketplace"
TIMEOUT_MS = 30000


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def is_blank_page(page: Page) -> bool:
    if page.url == "about:blank":
        return True

    title = (page.title() or "").strip()
    body = page.locator("body").inner_text().strip() if page.locator("body").count() else ""
    return not title and not body


def wait_for_full_load(page: Page) -> None:
    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)


def open_marketplace(page: Page) -> None:
    page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
    wait_for_full_load(page)


def main() -> None:
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=False,
            args=[f"--profile-directory={PROFILE_DIRECTORY}"],
        )

        try:
            page = context.new_page()

            try:
                open_marketplace(page)
            except (PlaywrightTimeoutError, PlaywrightError) as exc:
                logger.warning("Initial navigation issue: %s", exc)

            if is_blank_page(page):
                logger.warning("Blank page detected. Retrying once.")
                page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                wait_for_full_load(page)

            if is_blank_page(page):
                logger.error("Failed to load Facebook Marketplace. Blank page persisted after retry.")
                return

            print("Session loaded successfully")
        finally:
            context.close()


if __name__ == "__main__":
    main()