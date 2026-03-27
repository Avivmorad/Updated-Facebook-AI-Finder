from app.extraction.post_extractor import (
    _extract_iso_datetime_from_href,
    _extract_iso_datetime_from_timestamp,
    _looks_like_publish_date_hint,
)


def test_extract_iso_datetime_from_href_reads_create_time_query_param():
    value = _extract_iso_datetime_from_href("https://www.facebook.com/groups/1/posts/2/?__tn__=%2CO%2CP-R&create_time=1774526400")
    assert value == "2026-03-26T12:00:00+00:00"


def test_extract_iso_datetime_from_timestamp_rejects_non_numeric_value():
    assert _extract_iso_datetime_from_timestamp("not-a-timestamp") == ""


def test_looks_like_publish_date_hint_accepts_relative_time_text():
    assert _looks_like_publish_date_hint("3 hours ago")
    assert _looks_like_publish_date_hint("לפני 4 שעות")


def test_looks_like_publish_date_hint_rejects_long_non_date_text():
    assert not _looks_like_publish_date_hint("This is a long sentence about furniture and delivery with no timestamp hint")
