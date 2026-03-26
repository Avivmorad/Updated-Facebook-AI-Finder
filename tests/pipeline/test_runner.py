from app.domain.ai import AIAnalysisEnvelope, AIMatchResult
from app.domain.input import UserQuery
from app.pipeline.runner import PipelineRunner


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
                match_score=91,
                detected_item="iPhone 13",
                match_reason="The post explicitly offers an iPhone 13.",
                confidence=88,
            ),
            success=True,
        )


class _FakeHistoryStore:
    def save_run(self, result):
        return "run_1"

    def load_runs(self, limit=None):
        return []

    def load_run(self, run_id):
        return None


def test_pipeline_runner_returns_ranked_relevant_results():
    runner = PipelineRunner(query_service=_FakeQueryService())
    runner._search_service = _FakeScraper()
    runner._ai_service = _FakeAIService()
    runner._history_store = _FakeHistoryStore()

    result = runner.run({"query": "iphone 13"})

    assert result.run_state.status.value == "completed"
    assert result.presented_results["total_results"] == 1
    assert result.ranked_posts[0]["match_score"] == 91.0
    assert result.presented_results["results_list"][0]["post_link"] == "https://www.facebook.com/groups/1/posts/2"
