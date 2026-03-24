from typing import Dict, Tuple

DEFAULT_LANGUAGE = "he"
DEFAULT_REQUIRE_IMAGE = True
DEFAULT_POST_AGE = "24h"
DEFAULT_GROUP_MODE = "all_groups"

POST_AGE_OPTIONS: Dict[str, str] = {
    "1h": "Past hour",
    "24h": "Past 24 hours",
    "3d": "Past 3 days",
    "7d": "Past 7 days",
    "30d": "Past 30 days",
}

FIXED_FORBIDDEN_WORDS: Tuple[str, ...] = (
    "damaged",
    "broken",
    "fake",
    "stolen",
    "replica",
    "not working",
)

REGION_OPTIONS: Tuple[str, ...] = (
    "north",
    "center",
    "south",
    "jerusalem",
    "haifa",
)

GROUP_MODES: Tuple[str, ...] = (
    "all_groups",
    "specific_groups",
)

GROUP_SOURCES: Tuple[str, ...] = (
    "user_groups",
    "external_group",
    "url_input",
)
