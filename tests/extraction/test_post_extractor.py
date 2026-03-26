from app.extraction.post_extractor import (
    _extract_iso_datetime_from_href,
    _extract_iso_datetime_from_timestamp,
)


def test_extract_iso_datetime_from_href_reads_create_time_query_param():
    value = _extract_iso_datetime_from_href("https://www.facebook.com/groups/1/posts/2/?__tn__=%2CO%2CP-R&create_time=1774526400")
    assert value == "2026-03-26T12:00:00+00:00"


def test_extract_iso_datetime_from_timestamp_rejects_non_numeric_value():
    assert _extract_iso_datetime_from_timestamp("not-a-timestamp") == ""
