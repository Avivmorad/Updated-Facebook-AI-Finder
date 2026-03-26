import os
from dataclasses import dataclass, field
from typing import List


def _env_text(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass
class BrowserConfig:
    facebook_home_url: str = field(default_factory=lambda: _env_text("FACEBOOK_HOME_URL", "https://www.facebook.com/"))
    base_url: str = field(
        default_factory=lambda: _env_text(
            "FACEBOOK_GROUPS_FEED_URL",
            "https://www.facebook.com/groups/feed/",
        )
    )
    chrome_user_data_dir: str = field(default_factory=lambda: _env_text("CHROME_USER_DATA_DIR", ""))
    chrome_profile_directory: str = field(default_factory=lambda: _env_text("CHROME_PROFILE_DIRECTORY", ""))
    screenshots_dir: str = field(default_factory=lambda: _env_text("FB_SCREENSHOTS_DIR", "data/tmp/post_screenshots"))
    headless: bool = field(default_factory=lambda: _env_bool("HEADLESS", False))
    timeout_ms: int = field(default_factory=lambda: _env_int("FB_TIMEOUT_MS", 15000))
    retries: int = field(default_factory=lambda: _env_int("FB_RETRIES", 2))
    max_scroll_rounds: int = field(default_factory=lambda: _env_int("FB_MAX_SCROLL_ROUNDS", 8))
    scroll_pause_ms: int = field(default_factory=lambda: _env_int("FB_SCROLL_PAUSE_MS", 800))
    selectors_result_cards: List[str] = field(
        default_factory=lambda: [
            "a[href*='/groups/'][href*='/posts/']",
            "a[href*='/posts/']",
            "a[href*='/permalink/']",
            "a[href*='permalink.php']",
        ]
    )
    selectors_load_more: List[str] = field(
        default_factory=lambda: [
            "div[role='button']:has-text('See more')",
            "button:has-text('See more')",
            "div[role='button']:has-text('Load more')",
            "button:has-text('Load more')",
        ]
    )
    selectors_filters_panel: List[str] = field(
        default_factory=lambda: [
            "div[role='button']:has-text('Filters')",
            "button:has-text('Filters')",
            "div[role='button']:has-text('Filter')",
            "button:has-text('Filter')",
            "div[role='button']:has-text('סינון')",
            "button:has-text('סינון')",
            "div[role='button']:has-text('פילטרים')",
            "button:has-text('פילטרים')",
        ]
    )
    selectors_recent_posts: List[str] = field(
        default_factory=lambda: [
            "div[role='button']:has-text('פוסטים אחרונים')",
            "button:has-text('פוסטים אחרונים')",
            "div[role='button']:has-text('Most recent')",
            "button:has-text('Most recent')",
            "div[role='button']:has-text('Recent posts')",
        ]
    )
    selectors_last_24_hours: List[str] = field(
        default_factory=lambda: [
            "div[role='button']:has-text('24 שעות אחרונות')",
            "button:has-text('24 שעות אחרונות')",
            "div[role='button']:has-text('Last 24 hours')",
            "button:has-text('Last 24 hours')",
        ]
    )
    selectors_post_ready: List[str] = field(
        default_factory=lambda: [
            "div[role='main']",
            "div[role='article']",
        ]
    )
    selectors_post_text: List[str] = field(
        default_factory=lambda: [
            "div[role='main'] div[data-ad-preview='message']",
            "div[role='article'] div[dir='auto']",
            "div[role='main'] div[dir='auto']",
        ]
    )
    selectors_post_publish: List[str] = field(
        default_factory=lambda: [
            "a[href*='create_time']",
            "abbr",
            "span[aria-hidden='false']",
        ]
    )
    selectors_post_images: List[str] = field(
        default_factory=lambda: [
            "div[role='article'] img[src^='http']",
            "div[role='main'] img[src^='http']",
            "a[href*='/photo/'] img[src^='http']",
        ]
    )


PlatformAccessConfig = BrowserConfig
