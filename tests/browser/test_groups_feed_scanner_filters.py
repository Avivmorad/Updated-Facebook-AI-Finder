import pytest

from app.browser.groups_feed_scanner import GroupsFeedScanner
from app.utils.app_errors import AppError


def test_apply_feed_filters_raises_when_recent_posts_filter_missing(monkeypatch):
    scanner = GroupsFeedScanner()
    dummy_page = object()

    monkeypatch.setattr(scanner, "_open_filters_panel_if_needed", lambda page: None)
    monkeypatch.setattr(scanner, "_try_select_recent_posts", lambda page: False)
    monkeypatch.setattr(scanner, "_verify_recent_filter_selected", lambda page: False)
    monkeypatch.setattr(scanner, "_try_select_last_24_hours", lambda page: True)

    with pytest.raises(AppError) as exc:
        scanner._apply_feed_filters(dummy_page)  # type: ignore[arg-type]
    assert exc.value.code == "ERR_FILTER_RECENT_NOT_FOUND"


def test_apply_feed_filters_raises_when_recent_posts_not_verified(monkeypatch):
    scanner = GroupsFeedScanner()
    dummy_page = object()

    monkeypatch.setattr(scanner, "_open_filters_panel_if_needed", lambda page: None)
    monkeypatch.setattr(scanner, "_try_select_recent_posts", lambda page: True)
    monkeypatch.setattr(scanner, "_verify_recent_filter_selected", lambda page: False)
    monkeypatch.setattr(scanner, "_try_select_last_24_hours", lambda page: True)

    with pytest.raises(AppError) as exc:
        scanner._apply_feed_filters(dummy_page)  # type: ignore[arg-type]
    assert exc.value.code == "ERR_FILTER_RECENT_NOT_FOUND"


def test_normalize_post_link_removes_tracking_query_params():
    scanner = GroupsFeedScanner()
    link = (
        "https://www.facebook.com/groups/123/posts/456/"
        "?__cft__[0]=abc&__tn__=%2CO%2CP-R&story_fbid=456&id=123"
    )
    normalized = scanner._normalize_post_link(link)
    assert "__cft__" not in normalized
    assert "__tn__" not in normalized
    assert "story_fbid=456" in normalized
    assert "id=123" in normalized


def test_normalize_post_link_rejects_non_post_facebook_link():
    scanner = GroupsFeedScanner()
    normalized = scanner._normalize_post_link("https://www.facebook.com/groups/123/")
    assert normalized == ""


def test_normalize_post_link_rejects_external_link():
    scanner = GroupsFeedScanner()
    normalized = scanner._normalize_post_link("https://example.com/item")
    assert normalized == ""
