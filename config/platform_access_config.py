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
class PlatformAccessConfig:
    facebook_home_url: str = field(default_factory=lambda: _env_text("FACEBOOK_HOME_URL", "https://www.facebook.com/"))
    base_url: str = field(default_factory=lambda: _env_text("FACEBOOK_MARKETPLACE_URL", "https://www.facebook.com/marketplace"))
    chrome_user_data_dir: str = field(default_factory=lambda: _env_text("CHROME_USER_DATA_DIR", ""))
    chrome_profile_directory: str = field(default_factory=lambda: _env_text("CHROME_PROFILE_DIRECTORY", ""))
    headless: bool = field(default_factory=lambda: _env_bool("HEADLESS", False))
    timeout_ms: int = field(default_factory=lambda: _env_int("FB_TIMEOUT_MS", 15000))
    retries: int = field(default_factory=lambda: _env_int("FB_RETRIES", 2))
    max_scroll_rounds: int = field(default_factory=lambda: _env_int("FB_MAX_SCROLL_ROUNDS", 8))
    scroll_pause_ms: int = field(default_factory=lambda: _env_int("FB_SCROLL_PAUSE_MS", 800))
    selectors_search_input: List[str] = field(
        default_factory=lambda: [
            "input[placeholder*='Search Marketplace']",
            "input[type='search']",
            "input[aria-label*='Search']",
        ]
    )
    selectors_result_cards: List[str] = field(
        default_factory=lambda: [
            "a[href*='/marketplace/item/']",
            "div[role='main'] a[href*='/marketplace/item/']",
        ]
    )
    selectors_title: List[str] = field(
        default_factory=lambda: [
            "span",
            "h3",
            "h2",
        ]
    )
    selectors_price: List[str] = field(
        default_factory=lambda: [
            "span:has-text('$')",
            "span:has-text('₪')",
            "span:has-text('€')",
        ]
    )
    selectors_region: List[str] = field(
        default_factory=lambda: [
            "span",
        ]
    )
    selectors_load_more: List[str] = field(
        default_factory=lambda: [
            "div[role='button']:has-text('See more')",
            "div[role='button']:has-text('Load more')",
            "button:has-text('See more')",
        ]
    )
    selectors_post_ready: List[str] = field(
        default_factory=lambda: [
            "div[role='main']",
            "h1",
            "h2",
        ]
    )
    selectors_post_title: List[str] = field(
        default_factory=lambda: [
            "h1",
            "h2",
            "div[role='main'] span",
        ]
    )
    selectors_post_text: List[str] = field(
        default_factory=lambda: [
            "div[role='main'] div[data-ad-preview='message']",
            "div[role='main'] div[dir='auto']",
        ]
    )
    selectors_post_price: List[str] = field(
        default_factory=lambda: [
            "div[role='main'] span:has-text('$')",
            "div[role='main'] span:has-text('₪')",
            "div[role='main'] span:has-text('€')",
        ]
    )
    selectors_post_location: List[str] = field(
        default_factory=lambda: [
            "div[role='main'] span",
        ]
    )
    selectors_post_publish: List[str] = field(
        default_factory=lambda: [
            "a[href*='create_time']",
            "div[role='main'] span",
        ]
    )
    selectors_post_seller: List[str] = field(
        default_factory=lambda: [
            "a[href*='/profile.php'] span",
            "a[href*='/marketplace/profile'] span",
            "div[role='main'] h3",
        ]
    )
    selectors_post_comments: List[str] = field(
        default_factory=lambda: [
            "div[role='article'] div[dir='auto']",
            "div[aria-label*='comment']",
        ]
    )
    selectors_post_signals: List[str] = field(
        default_factory=lambda: [
            "div[role='main'] span",
            "div[role='main'] a",
        ]
    )
