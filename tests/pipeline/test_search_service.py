from app.pipeline.search_service import SearchService


class _FakeExtraction:
    normalized_post_data = {
        "post_link": "https://www.facebook.com/groups/1/posts/2",
        "post_id": "2",
        "post_text": "Selling iPhone 13",
        "images": ["https://img/1"],
        "image_count": 1,
        "publish_date_raw": "",
        "publish_date_normalized": "",
        "extraction_quality": "partial",
        "post_screenshot_path": "data/tmp/post_screenshots/post_1.png",
        "screenshot_paths": ["data/tmp/post_screenshots/post_1.png"],
        "publish_date": "",
    }
    raw_post_data = {
        "post_text": "Selling iPhone 13",
        "post_screenshot_path": "data/tmp/post_screenshots/post_1.png",
    }
    warnings = []
    error = None
    success = True


class _FakePostExtractor:
    def extract_post(self, opened_post):
        return _FakeExtraction()


def test_collect_post_data_keeps_publish_fields_and_returns_screenshot_path():
    service = SearchService()
    service._post_extractor = _FakePostExtractor()

    payload = service.collect_post_data(
        {
            "post_id": "1",
            "post_link": "https://www.facebook.com/groups/1/posts/2",
            "preview_text": "\u200f6 \u05e9\u05e2\u05d5\u05ea",
        }
    )

    assert payload["publish_date_raw"] == ""
    assert payload["publish_date_normalized"] == ""
    assert payload["publish_date"] == ""
    assert payload["post_screenshot_path"] == "data/tmp/post_screenshots/post_1.png"
    assert payload["extraction_quality"] == "partial"
    assert payload["image_count"] == 1


def test_collect_posts_from_links_runs_extraction_for_each_link():
    service = SearchService()
    service._post_extractor = _FakePostExtractor()

    payload = service.collect_posts_from_links(
        [
            "https://www.facebook.com/groups/1/posts/2",
            "https://www.facebook.com/groups/1/posts/3",
        ]
    )

    assert len(payload) == 2
    assert all(item["post_screenshot_path"] == "data/tmp/post_screenshots/post_1.png" for item in payload)
