from app.extraction.post_extractor import (
    _extract_iso_datetime_from_href,
    _extract_iso_datetime_from_timestamp,
    _looks_like_publish_date_hint,
    _normalize_post_permalink_href,
    _select_best_container_candidate,
    _select_best_permalink_candidate,
    _select_best_text_candidate,
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


def test_normalize_post_permalink_href_removes_comment_query_params():
    href = "https://www.facebook.com/groups/123/posts/456/?comment_id=999&reply_comment_id=1000&__tn__=R"

    normalized = _normalize_post_permalink_href(href)

    assert normalized == "https://www.facebook.com/groups/123/posts/456/"


def test_normalize_post_permalink_href_rejects_photo_links():
    href = (
        "https://www.facebook.com/photo/?fbid=10164320041509939"
        "&set=gm.1253893039669796"
    )

    normalized = _normalize_post_permalink_href(href)

    assert normalized == ""


def test_normalize_post_permalink_href_rejects_group_home_links():
    href = "https://www.facebook.com/groups/Pishpeshuk.Handover/"

    normalized = _normalize_post_permalink_href(href)

    assert normalized == ""


def test_select_best_text_candidate_prefers_visible_large_text_block():
    candidates = [
        {"text": "מחיר", "visible": True, "width": 18.0, "height": 9.0, "selector": "div[role='article'] div[dir='auto']"},
        {
            "text": "מוכרת כוננית מעץ מלא במצב מצוין, איסוף מיידי.",
            "visible": True,
            "width": 420.0,
            "height": 88.0,
            "selector": "div[role='article'] div[data-ad-preview='message']",
        },
    ]

    best = _select_best_text_candidate(candidates)

    assert best is not None
    assert best["text"] == "מוכרת כוננית מעץ מלא במצב מצוין, איסוף מיידי."


def test_select_best_permalink_candidate_avoids_tiny_hidden_anchor():
    candidates = [
        {
            "href": "https://www.facebook.com/groups/123/posts/456/",
            "visible": True,
            "width": 8.0,
            "height": 6.0,
            "label_length": 0,
            "label_text": "",
            "selector": "a[href*='/posts/']",
        },
        {
            "href": "https://www.facebook.com/groups/123/posts/456/",
            "visible": True,
            "width": 180.0,
            "height": 28.0,
            "label_length": 6,
            "label_text": "2 שעות",
            "selector": "a[href*='/posts/']",
        },
    ]

    best = _select_best_permalink_candidate(candidates)

    assert best is not None
    assert best["width"] == 180.0


def test_select_best_container_candidate_prefers_article_over_main_wrapper():
    candidates = [
        {
            "selector": "div[role='main']",
            "role": "main",
            "visible": True,
            "width": 1280.0,
            "height": 4200.0,
            "text_length": 1000,
            "permalink_count": 0,
            "photo_link_count": 4,
            "image_count": 8,
            "action_count": 12,
            "article_descendant_count": 3,
            "action_text": "",
        },
        {
            "selector": "div[role='article']",
            "role": "article",
            "visible": True,
            "width": 760.0,
            "height": 980.0,
            "text_length": 340,
            "permalink_count": 1,
            "photo_link_count": 0,
            "image_count": 3,
            "action_count": 4,
            "article_descendant_count": 0,
            "action_text": "Like | Comment | Share",
        },
    ]

    best = _select_best_container_candidate(candidates)

    assert best is not None
    assert best["selector"] == "div[role='article']"
