from datetime import datetime, timezone

from app.pipeline.time_filter import RecentPostFilter


def test_time_filter_keeps_recent_relative_publish_date():
    filter_ = RecentPostFilter()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    assert filter_.is_recent_publish_date("2 hours ago", now=now) is True


def test_time_filter_rejects_old_relative_publish_date():
    filter_ = RecentPostFilter()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    assert filter_.is_recent_publish_date("2 days ago", now=now) is False


def test_time_filter_rejects_unparseable_publish_date():
    filter_ = RecentPostFilter()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    assert filter_.is_recent_publish_date("sometime maybe", now=now) is False


def test_time_filter_keeps_today_with_clock_time():
    filter_ = RecentPostFilter()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    assert filter_.is_recent_publish_date("Today at 11:30 AM", now=now) is True


def test_time_filter_keeps_english_month_day_time_format():
    filter_ = RecentPostFilter()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    assert filter_.is_recent_publish_date("March 26 at 10:15 AM", now=now) is True


def test_time_filter_rejects_old_english_month_day_time_format():
    filter_ = RecentPostFilter()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    assert filter_.is_recent_publish_date("March 20 at 10:15 AM", now=now) is False


def test_time_filter_keeps_recent_hebrew_hours_value():
    filter_ = RecentPostFilter()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    assert filter_.is_recent_publish_date("\u200f6 \u05e9\u05e2\u05d5\u05ea", now=now) is True


def test_time_filter_rejects_old_hebrew_days_value():
    filter_ = RecentPostFilter()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    assert filter_.is_recent_publish_date("2 \u05d9\u05de\u05d9\u05dd", now=now) is False
