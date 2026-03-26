import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set


_RELATIVE_MINUTES = re.compile(r"(\d+)\s*(?:m|min|mins|minute|minutes)\b", re.IGNORECASE)
_RELATIVE_HOURS = re.compile(r"(\d+)\s*(?:h|hr|hrs|hour|hours)\b", re.IGNORECASE)
_RELATIVE_DAYS = re.compile(r"(\d+)\s*(?:d|day|days)\b", re.IGNORECASE)
_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


class RecentPostFilter:
    def filter_posts(self, posts: List[Dict[str, object]], request: object) -> List[Dict[str, object]]:
        filtered, _ = self.filter_posts_with_diagnostics(posts, request)
        return filtered

    def filter_posts_with_diagnostics(
        self,
        posts: List[Dict[str, object]],
        request: object,
        existing_urls: Optional[Set[str]] = None,
        now: Optional[datetime] = None,
    ) -> tuple[List[Dict[str, object]], List[Dict[str, str]]]:
        _ = request
        _ = existing_urls
        reference_now = now or datetime.now(timezone.utc)

        filtered: List[Dict[str, object]] = []
        rejected: List[Dict[str, str]] = []

        for post in posts:
            publish_date = str(post.get("publish_date") or "").strip()
            if self.is_recent_publish_date(publish_date, now=reference_now):
                filtered.append(post)
            else:
                rejected.append(
                    {
                        "post_link": str(post.get("post_link") or "").strip(),
                        "reason": "older_than_24_hours_or_unparseable_publish_date",
                    }
                )

        return filtered, rejected

    def is_recent_publish_date(self, publish_date: str, now: Optional[datetime] = None) -> bool:
        reference_now = now or datetime.now(timezone.utc)
        parsed = _parse_publish_date(publish_date, reference_now)
        if parsed is None:
            return False
        return (reference_now - parsed) <= timedelta(hours=24)


def _parse_publish_date(value: str, reference_now: datetime) -> Optional[datetime]:
    text = value.strip()
    if not text:
        return None

    lowered = text.lower()
    if "today" in lowered:
        return reference_now
    if "yesterday" in lowered:
        return reference_now - timedelta(hours=24)

    minutes_match = _RELATIVE_MINUTES.search(lowered)
    if minutes_match:
        return reference_now - timedelta(minutes=int(minutes_match.group(1)))

    hours_match = _RELATIVE_HOURS.search(lowered)
    if hours_match:
        return reference_now - timedelta(hours=int(hours_match.group(1)))

    days_match = _RELATIVE_DAYS.search(lowered)
    if days_match:
        return reference_now - timedelta(days=int(days_match.group(1)))

    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    for date_format in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, date_format)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    return None
