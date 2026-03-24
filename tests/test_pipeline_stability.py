import unittest
from typing import Any, cast

from app.logic.initial_filter import InitialFilter
from app.logic.pipeline_runner import PipelineRunner
from app.models.input_models import SearchRequest
from app.models.pipeline_models import PipelineOptions, RunStatus


class _FakeInputService:
    def validate_and_build(self, raw_user_input):
        request = SearchRequest(
            query_text="iphone 13",
            tags=["apple"],
            secondary_attributes=["128gb"],
            forbidden_words=[],
            min_price=None,
            max_price=None,
            is_free=False,
            post_age="24h",
            require_image=False,
            language="he",
            target_regions=["center"],
            all_country=False,
            group_mode="all_groups",
            groups=[],
            group_sources=["user_groups"],
            group_urls=[],
            select_all_groups=False,
        )
        return request, []


class _FakeScraper:
    def __init__(self):
        self._open_calls = 0

    def search_posts(self, request, max_posts):
        return [
            {
                "post_id": "bad",
                "title": "iphone 13 bad post",
                "region": "center",
                "url": "http://bad",
                "snippet": "bad",
            },
            {
                "post_id": "good",
                "title": "iphone 13 good post",
                "region": "center",
                "url": "http://good",
                "snippet": "good",
            },
        ]

    def open_post(self, post):
        self._open_calls += 1
        if post.get("post_id") == "bad":
            raise RuntimeError("temporary_open_failure")
        return post

    def collect_post_data(self, opened_post):
        return {
            **opened_post,
            "raw_post_data": {"title": opened_post.get("title"), "post_url": opened_post.get("url")},
            "normalized_post_data": {
                "title": opened_post.get("title"),
                "text": opened_post.get("snippet"),
                "price": 2000.0,
                "location": opened_post.get("region"),
                "publish_time": "1h",
                "seller_name": "tester",
                "comments": ["available"],
                "images": ["img-1"],
                "important_visible_signals": ["available"],
                "url": opened_post.get("url"),
            },
            "description": opened_post.get("snippet"),
            "price": 2000.0,
            "has_image": True,
            "publish_age": "1h",
            "post_url": opened_post.get("url"),
            "images": ["img-1"],
            "seller_name": "tester",
            "comments": ["available"],
            "important_visible_signals": ["available"],
            "extraction_warnings": [],
            "extraction_error": None,
            "extraction_success": True,
        }


class _FakeLogicAnalyzer:
    def reset_session(self):
        return None

    def analyze(self, collected, request):
        return {
            "logic_score": 0.8,
            "completeness_score": 0.9,
            "warning_flags": [],
            "suspicious_indicators": [],
            "seller_signal": {"quality": "ok", "indicators": []},
            "comment_signal": {"positive_count": 1, "negative_count": 0},
            "duplicate": {"is_duplicate": False},
        }


class _FakeAIAnalyzer:
    def analyze(self, collected, request):
        return {
            "relevance_score": 0.82,
            "warning_signs": [],
            "recommendation": "buy",
            "image_product_match": "match",
            "ai_fallback_used": False,
        }


class _FakeHistoryStore:
    def save_run(self, result):
        return "run_test"

    def load_runs(self, limit=None):
        return []

    def load_run(self, run_id):
        return None


class PipelineStabilityTests(unittest.TestCase):
    def _build_runner(self):
        runner = PipelineRunner(input_service=cast(Any, _FakeInputService()))
        cast(Any, runner)._scraper = _FakeScraper()
        cast(Any, runner)._logic_analyzer = _FakeLogicAnalyzer()
        cast(Any, runner)._ai_analyzer = _FakeAIAnalyzer()
        cast(Any, runner)._history_store = _FakeHistoryStore()
        return runner

    def test_pipeline_continues_after_non_fatal_post_error(self):
        runner = self._build_runner()

        result = runner.run(raw_user_input={"main_text": "iphone"}, options=PipelineOptions(max_posts=5))

        self.assertEqual(result.run_state.status, RunStatus.COMPLETED)
        self.assertEqual(len(result.ranked_posts), 1)
        notices = result.presented_results.get("pipeline_notices", [])
        self.assertTrue(any(str(item).startswith("non_fatal_post_errors=") for item in notices))

    def test_pipeline_stops_when_continue_on_post_error_disabled(self):
        runner = self._build_runner()

        result = runner.run(
            raw_user_input={"main_text": "iphone"},
            options=PipelineOptions(max_posts=5, continue_on_post_error=False),
        )

        self.assertEqual(result.run_state.status, RunStatus.STOPPED)
        self.assertEqual(result.run_state.stop_reason, "post_error_and_continue_disabled")

    def test_initial_filter_accepts_partial_query_term_match(self):
        request = SearchRequest(
            query_text="iphone 13",
            tags=["apple"],
            secondary_attributes=["128gb"],
            forbidden_words=[],
            min_price=None,
            max_price=None,
            is_free=False,
            post_age="24h",
            require_image=False,
            language="he",
            target_regions=[],
            all_country=False,
            group_mode="all_groups",
            groups=[],
            group_sources=["user_groups"],
            group_urls=[],
            select_all_groups=False,
        )

        filtered = InitialFilter().filter_posts(
            [
                {"post_id": "1", "title": "Apple smartphone 128GB", "snippet": "great condition"},
                {"post_id": "2", "title": "Wooden table", "snippet": "furniture"},
            ],
            request,
        )

        self.assertEqual([item["post_id"] for item in filtered], ["1"])

    def test_initial_filter_keeps_marketplace_item_when_card_text_is_weak(self):
        request = SearchRequest(
            query_text="iphone 13",
            tags=["apple"],
            secondary_attributes=["128gb"],
            forbidden_words=[],
            min_price=None,
            max_price=None,
            is_free=False,
            post_age="24h",
            require_image=False,
            language="he",
            target_regions=[],
            all_country=False,
            group_mode="all_groups",
            groups=[],
            group_sources=["user_groups"],
            group_urls=[],
            select_all_groups=False,
        )

        filtered = InitialFilter().filter_posts(
            [
                {
                    "post_id": "1",
                    "title": "240 US$",
                    "snippet": "240 US$",
                    "url": "https://www.facebook.com/marketplace/item/1257246286496670/",
                }
            ],
            request,
        )

        self.assertEqual([item["post_id"] for item in filtered], ["1"])


if __name__ == "__main__":
    unittest.main()
