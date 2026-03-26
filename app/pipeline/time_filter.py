import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set


_RELATIVE_MINUTES = re.compile(r"(\d+)\s*(?:m|min|mins|minute|minutes)\b", re.IGNORECASE)
_RELATIVE_HOURS = re.compile(r"(\d+)\s*(?:h|hr|hrs|hour|hours)\b", re.IGNORECASE)
_RELATIVE_DAYS = re.compile(r"(\d+)\s*(?:d|day|days)\b", re.IGNORECASE)
_RELATIVE_MINUTES_HE = re.compile(r"(\d+)\s*(?:דקה|דקות)\b")
_RELATIVE_HOURS_HE = re.compile(r"(\d+)\s*(?:שעה|שעות)\b")
_RELATIVE_DAYS_HE = re.compile(r"(\d+)\s*(?:יום|ימים)\b")
_TIME_OF_DAY = re.compile(r"(\d{1,2}):(\d{2})\s*([ap]m)", re.IGNORECASE)
_WEEKDAY_AT_TIME = re.compile(
    r"\b(monday|mon|tuesday|tue|wednesday|wed|thursday|thu|friday|fri|saturday|sat|sunday|sun)\b(?:\s+at\s+|\s+)(\d{1,2}:\d{2}\s*[ap]m)",
    re.IGNORECASE,
)
_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)
_MONTH_DAY_FORMATS = (
    "%B %d at %I:%M %p",
    "%b %d at %I:%M %p",
    "%B %d, %Y at %I:%M %p",
    "%b %d, %Y at %I:%M %p",
    "%B %d",
    "%b %d",
)
_WEEKDAY_INDEX = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


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
    text = _normalize_publish_text(value)
    if not text:
        return None

    lowered = text.lower()
    relative_named = _parse_named_day_with_optional_time(lowered, reference_now)
    if relative_named is not None:
        return relative_named

    minutes_match = _RELATIVE_MINUTES.search(lowered)
    if minutes_match:
        return reference_now - timedelta(minutes=int(minutes_match.group(1)))

    minutes_match_he = _RELATIVE_MINUTES_HE.search(text)
    if minutes_match_he:
        return reference_now - timedelta(minutes=int(minutes_match_he.group(1)))

    hours_match = _RELATIVE_HOURS.search(lowered)
    if hours_match:
        return reference_now - timedelta(hours=int(hours_match.group(1)))

    hours_match_he = _RELATIVE_HOURS_HE.search(text)
    if hours_match_he:
        return reference_now - timedelta(hours=int(hours_match_he.group(1)))

    days_match = _RELATIVE_DAYS.search(lowered)
    if days_match:
        return reference_now - timedelta(days=int(days_match.group(1)))

    days_match_he = _RELATIVE_DAYS_HE.search(text)
    if days_match_he:
        return reference_now - timedelta(days=int(days_match_he.group(1)))

    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    weekday_value = _parse_weekday_at_time(lowered, reference_now)
    if weekday_value is not None:
        return weekday_value

    month_day_value = _parse_month_day_text(text, reference_now)
    if month_day_value is not None:
        return month_day_value

    for date_format in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, date_format)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    return None


def _normalize_publish_text(value: str) -> str:
    return (
        value.strip()
        .replace("\u200e", "")
        .replace("\u200f", "")
        .replace("\u202a", "")
        .replace("\u202b", "")
        .replace("\u202c", "")
    )


def _parse_named_day_with_optional_time(lowered: str, reference_now: datetime) -> Optional[datetime]:
    if "today" in lowered:
        base = reference_now
        return _apply_time_of_day(base, lowered) or base

    if "yesterday" in lowered:
        base = reference_now - timedelta(days=1)
        return _apply_time_of_day(base, lowered) or base

    return None


def _apply_time_of_day(base: datetime, text: str) -> Optional[datetime]:
    match = _TIME_OF_DAY.search(text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = match.group(3).lower()

    if hour == 12:
        hour = 0
    if meridiem == "pm":
        hour += 12

    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _parse_weekday_at_time(lowered: str, reference_now: datetime) -> Optional[datetime]:
    match = _WEEKDAY_AT_TIME.search(lowered)
    if not match:
        return None

    weekday_name = match.group(1).lower()
    target_weekday = _WEEKDAY_INDEX.get(weekday_name)
    if target_weekday is None:
        return None

    days_back = (reference_now.weekday() - target_weekday) % 7
    base = reference_now - timedelta(days=days_back)
    value = _apply_time_of_day(base, match.group(2))
    return value or base


def _parse_month_day_text(text: str, reference_now: datetime) -> Optional[datetime]:
    cleaned = text.strip()
    for date_format in _MONTH_DAY_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, date_format)
        except ValueError:
            continue

        if "%Y" not in date_format:
            parsed = parsed.replace(year=reference_now.year)

        parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed > reference_now + timedelta(days=1):
            parsed = parsed.replace(year=parsed.year - 1)
        return parsed

    return None
