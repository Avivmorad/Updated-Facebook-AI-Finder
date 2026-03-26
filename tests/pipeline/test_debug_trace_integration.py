from app.domain.ai import AIAnalysisEnvelope, AIMatchResult
from app.domain.input import UserQuery
from app.pipeline.runner import PipelineRunner
from app.utils.debugging import close_debugging, configure_debugging


class _FakeQueryService:
    def validate_and_build(self, raw_user_input):
        return UserQuery(query=str(raw_user_input["query"])), []


class _FakeScraper:
    def search_posts(self, user_query, max_posts):
        return [{"post_id": "1", "post_link": "https://www.facebook.com/groups/1/posts/2"}]

    def open_post(self, post_summary):
        return dict(post_summary)

    def collect_post_data(self, opened_post):
        return {
            "post_id": opened_post["post_id"],
            "post_link": opened_post["post_link"],
            "post_text": "Selling iPhone 13",
            "images": ["https://img/1"],
            "publish_date": "2 hours ago",
            "post_screenshot_path": "data/tmp/post_screenshots/post_1.png",
            "raw_post_data": {},
            "normalized_post_data": {
                "post_link": opened_post["post_link"],
                "post_text": "Selling iPhone 13",
                "images": ["https://img/1"],
                "publish_date": "2 hours ago",
            },
            "extraction_warnings": [],
            "extraction_error": None,
            "extraction_success": True,
        }


class _FakeAIService:
    def analyze(self, post_data, user_query):
        return AIAnalysisEnvelope(
            result=AIMatchResult(
                is_relevant=True,
                match_score=90,
                detected_item="iPhone 13",
                match_reason="Found exact item.",
                confidence=92,
                is_recent_24h=True,
                publish_date_observed="2 hours ago",
                publish_date_reason="Visible in screenshot",
                publish_date_confidence=94,
            ),
            success=True,
        )


class _FakeHistoryStore:
    def save_run(self, result):
        return "run_test"

    def load_runs(self, limit=None):
        return []

    def load_run(self, run_id):
        return None


def test_pipeline_run_writes_debug_trace_file(tmp_path):
    trace_path = tmp_path / "debug_trace.txt"
    configure_debugging(True, str(trace_path))
    try:
        runner = PipelineRunner(query_service=_FakeQueryService())
        runner._search_service = _FakeScraper()
        runner._ai_service = _FakeAIService()
        runner._history_store = _FakeHistoryStore()

        result = runner.run({"query": "iphone 13"})
        assert result.run_state.status.value == "completed"
    finally:
        close_debugging()

    assert trace_path.exists() is True
    text = trace_path.read_text(encoding="utf-8")
    assert "DBG_PIPELINE_START" in text
    assert "DBG_STAGE_1_INPUT" in text
    assert "DBG_PRESENT_DONE" in text
