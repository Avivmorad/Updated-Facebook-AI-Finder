import json
import unittest

from app.ai.ai_client import AIClientResult, GeminiClient, GroqClient, build_default_ai_client
from app.ai.ai_service import AIAnalysisService
from app.models.input_models import SearchRequest
from config.ai_analysis_config import AIAnalysisConfig


class _FakeAIClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0

    def generate(self, prompt):
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        response = self.responses[index]
        if isinstance(response, Exception):
            return AIClientResult(raw_text="", raw_data={}, error=str(response))
        return response


def _request() -> SearchRequest:
    return SearchRequest(
        query_text="iphone 13",
        tags=[],
        secondary_attributes=[],
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


class AIServiceResilienceTests(unittest.TestCase):
    def test_build_default_client_uses_groq_provider(self):
        client = build_default_ai_client(AIAnalysisConfig(provider="groq"))
        self.assertIsInstance(client, GroqClient)

    def test_build_default_client_supports_gemini_provider(self):
        client = build_default_ai_client(AIAnalysisConfig(provider="gemini"))
        self.assertIsInstance(client, GeminiClient)

    def test_retries_then_success_without_fallback(self):
        valid_payload = {
            "post_meaning": "listing",
            "seller_intent": "sell",
            "reliability_signals": [],
            "pros": [],
            "cons": [],
            "warning_signs": [],
            "recommendation": "buy",
            "image_product_match": "match",
            "logic_notes": "ok",
            "relevance_score": 0.9,
        }

        fake_client = _FakeAIClient(
            [
                AIClientResult(raw_text="", raw_data={}, error="temporary_ai_error"),
                AIClientResult(raw_text=json.dumps(valid_payload), raw_data={}),
            ]
        )
        service = AIAnalysisService(
            ai_client=fake_client,
            config=AIAnalysisConfig(retry_attempts=2, retry_backoff_seconds=0.0),
        )

        envelope = service.analyze(post_data={"title": "iphone 13"}, request=_request())

        self.assertFalse(envelope.fallback_used)
        self.assertTrue(envelope.success)
        self.assertEqual(fake_client.calls, 2)

    def test_fallback_after_all_attempts_fail(self):
        fake_client = _FakeAIClient(
            [
                AIClientResult(raw_text="", raw_data={}, error="network_error"),
                AIClientResult(raw_text="", raw_data={}, error="network_error"),
            ]
        )
        service = AIAnalysisService(
            ai_client=fake_client,
            config=AIAnalysisConfig(retry_attempts=1, retry_backoff_seconds=0.0),
        )

        envelope = service.analyze(post_data={"title": "iphone 13"}, request=_request())

        self.assertTrue(envelope.fallback_used)
        self.assertFalse(envelope.success)
        self.assertTrue(envelope.validation_errors)
        self.assertEqual(fake_client.calls, 2)


if __name__ == "__main__":
    unittest.main()
