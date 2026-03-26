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
