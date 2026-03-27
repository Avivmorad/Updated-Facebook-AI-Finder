from app.extraction.post_normalizer import normalize_post_data


def test_normalize_post_data_builds_extended_schema():
    result = normalize_post_data(
        {
            "post_link": "https://www.facebook.com/groups/1/posts/2",
            "post_id": "2",
            "post_text": "  iPhone   13   for sale  ",
            "images": ["https://img/1", "https://img/1", "https://img/2"],
            "publish_date_raw": "\u200f2 \u05e9\u05e2\u05d5\u05ea",
            "publish_date_normalized": "2 \u05e9\u05e2\u05d5\u05ea",
            "post_screenshot_path": "data/tmp/post_screenshots/post_1.png",
            "seller_name": "ignored",
            "comments": ["ignored"],
        }
    )

    assert result == {
        "post_link": "https://www.facebook.com/groups/1/posts/2",
        "post_id": "2",
        "post_text": "iPhone 13 for sale",
        "images": ["https://img/1", "https://img/2"],
        "image_count": 2,
        "publish_date_raw": "2 \u05e9\u05e2\u05d5\u05ea",
        "publish_date_normalized": "2 \u05e9\u05e2\u05d5\u05ea",
        "extraction_quality": "good",
        "post_screenshot_path": "data/tmp/post_screenshots/post_1.png",
        "screenshot_paths": ["data/tmp/post_screenshots/post_1.png"],
        "publish_date": "2 \u05e9\u05e2\u05d5\u05ea",
    }


def test_normalize_post_data_marks_partial_or_failed_quality():
    partial = normalize_post_data({"post_link": "https://www.facebook.com/groups/1/posts/2", "post_text": "Only text"})
    failed = normalize_post_data({"post_link": "", "post_text": "", "images": []})

    assert partial["extraction_quality"] == "partial"
    assert failed["extraction_quality"] == "failed"
