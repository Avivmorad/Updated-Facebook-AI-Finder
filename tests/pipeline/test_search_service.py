from app.pipeline.search_service import SearchService


class _FakeExtraction:
    normalized_post_data = {
        "post_link": "https://www.facebook.com/groups/1/posts/2",
        "post_text": "Selling iPhone 13",
        "images": ["https://img/1"],
        "publish_date": "",
    }
    raw_post_data = {"post_text": "Selling iPhone 13"}
    warnings = []
    error = None
    success = True


class _FakePostExtractor:
    def extract_post(self, opened_post):
        return _FakeExtraction()


def test_collect_post_data_falls_back_to_preview_text_for_publish_date():
    service = SearchService()
    service._post_extractor = _FakePostExtractor()

    payload = service.collect_post_data(
        {
            "post_id": "1",
            "post_link": "https://www.facebook.com/groups/1/posts/2",
            "preview_text": "\u200f6 \u05e9\u05e2\u05d5\u05ea",
        }
    )

    assert payload["publish_date"] == "\u200f6 \u05e9\u05e2\u05d5\u05ea"
