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
    step_debug_enabled: bool = field(default_factory=lambda: _env_bool("FB_STEP_DEBUG_ENABLED", False))
    step_debug_dir: str = field(default_factory=lambda: _env_text("FB_STEP_DEBUG_DIR", "data/logs/browser_steps"))
    slow_mo_ms: int = field(default_factory=lambda: _env_int("FB_SLOW_MO_MS", 0))
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
            "a[href*='/share/p/']",
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
            "div[role='button']:has-text('\u05e1\u05d9\u05e0\u05d5\u05df')",
            "button:has-text('\u05e1\u05d9\u05e0\u05d5\u05df')",
            "div[role='button']:has-text('\u05e4\u05d9\u05dc\u05d8\u05e8\u05d9\u05dd')",
            "button:has-text('\u05e4\u05d9\u05dc\u05d8\u05e8\u05d9\u05dd')",
        ]
    )
    selectors_recent_posts: List[str] = field(
        default_factory=lambda: [
            "div[role='button']:has-text('\u05e4\u05d5\u05e1\u05d8\u05d9\u05dd \u05d0\u05d7\u05e8\u05d5\u05e0\u05d9\u05dd')",
            "button:has-text('\u05e4\u05d5\u05e1\u05d8\u05d9\u05dd \u05d0\u05d7\u05e8\u05d5\u05e0\u05d9\u05dd')",
            "div[role='button']:has-text('\u05d4\u05d7\u05d3\u05e9\u05d9\u05dd \u05d1\u05d9\u05d5\u05ea\u05e8')",
            "button:has-text('\u05d4\u05d7\u05d3\u05e9\u05d9\u05dd \u05d1\u05d9\u05d5\u05ea\u05e8')",
            "div[role='button']:has-text('Most recent')",
            "button:has-text('Most recent')",
            "div[role='button']:has-text('Recent posts')",
            "button:has-text('Recent posts')",
            "div[role='button']:has-text('Newest')",
            "button:has-text('Newest')",
            "div[role='button']:has-text('Latest')",
            "button:has-text('Latest')",
        ]
    )
    selectors_last_24_hours: List[str] = field(
        default_factory=lambda: [
            "div[role='button']:has-text('24 \u05e9\u05e2\u05d5\u05ea \u05d0\u05d7\u05e8\u05d5\u05e0\u05d5\u05ea')",
            "button:has-text('24 \u05e9\u05e2\u05d5\u05ea \u05d0\u05d7\u05e8\u05d5\u05e0\u05d5\u05ea')",
            "div[role='button']:has-text('Last 24 hours')",
            "button:has-text('Last 24 hours')",
            "div[role='button']:has-text('Past 24 hours')",
            "button:has-text('Past 24 hours')",
        ]
    )
    selectors_post_container: List[str] = field(
        default_factory=lambda: [
            "div[role='article']",
            "div[data-pagelet='MainFeed'] div[role='article']",
            "div[role='main'] div[role='article']",
            "div[role='main']",
        ]
    )
    selectors_expand_post_text: List[str] = field(
        default_factory=lambda: [
            "div[role='button']:has-text('See more')",
            "span:has-text('See more')",
            "div[role='button']:has-text('\u05e8\u05d0\u05d4 \u05e2\u05d5\u05d3')",
            "span:has-text('\u05e8\u05d0\u05d4 \u05e2\u05d5\u05d3')",
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
            "div[role='article'] div[data-ad-preview='message']",
            "div[role='article'] div[dir='auto']",
            "div[role='main'] div[dir='auto']",
        ]
    )
    selectors_post_publish: List[str] = field(
        default_factory=lambda: [
            "a[href*='create_time']",
            "a[href*='/posts/'][aria-label]",
            "a[aria-label*='ago']",
            "a[aria-label*='\u05dc\u05e4\u05e0\u05d9']",
            "span[aria-label*='ago']",
            "span[aria-label*='\u05dc\u05e4\u05e0\u05d9']",
            "a[href*='/posts/'] span[dir='auto']",
            "abbr",
            "span[aria-hidden='false']",
        ]
    )
    selectors_post_permalink: List[str] = field(
        default_factory=lambda: [
            "a[href*='/posts/']",
            "a[href*='/permalink/']",
            "a[href*='story_fbid=']",
            "a[href*='fbid=']",
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
