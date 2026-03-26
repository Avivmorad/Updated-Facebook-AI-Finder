from app.ai.ai_client import AIClientResult
from app.ai.ai_service import AIAnalysisService
from app.config.ai import AIConfig
from app.domain.input import UserQuery


class _FakeAIClient:
    def __init__(self, result: AIClientResult) -> None:
        self._result = result

    def generate(self, prompt):
        return self._result


def _sample_post_data():
    return {
        "post_text": "Selling iPhone 13 in good condition",
        "images": [],
        "post_link": "https://www.facebook.com/groups/1/posts/2",
        "publish_date": "2 hours ago",
    }


def test_ai_service_maps_invalid_json_to_specific_error_code():
    service = AIAnalysisService(
        ai_client=_FakeAIClient(AIClientResult(raw_text="this is not json", raw_data={})),
        config=AIConfig(retry_attempts=0),
    )

    envelope = service.analyze(_sample_post_data(), UserQuery(query="iphone 13"))
    assert envelope.success is False
    assert envelope.validation_errors == ["ERR_AI_RESPONSE_INVALID_JSON"]


def test_ai_service_maps_empty_response_to_specific_error_code():
    service = AIAnalysisService(
        ai_client=_FakeAIClient(AIClientResult(raw_text="", raw_data={})),
        config=AIConfig(retry_attempts=0),
    )

    envelope = service.analyze(_sample_post_data(), UserQuery(query="iphone 13"))
    assert envelope.success is False
    assert envelope.validation_errors == ["ERR_AI_RESPONSE_EMPTY"]


def test_ai_service_maps_request_error_to_specific_error_code():
    service = AIAnalysisService(
        ai_client=_FakeAIClient(AIClientResult(raw_text="", raw_data={}, error="network timeout")),
        config=AIConfig(retry_attempts=0),
    )

    envelope = service.analyze(_sample_post_data(), UserQuery(query="iphone 13"))
    assert envelope.success is False
    assert envelope.validation_errors == ["ERR_AI_REQUEST_FAILED"]
