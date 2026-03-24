from typing import Any, Dict

from app.ai.ai_service import AIAnalysisService
from app.models.input_models import SearchRequest


class AIAnalyzer:
    def __init__(self, ai_service: AIAnalysisService | None = None) -> None:
        self._ai_service = ai_service or AIAnalysisService()

    def analyze(self, post_data: Dict[str, Any], request: SearchRequest) -> Dict[str, Any]:
        envelope = self._ai_service.analyze(post_data=post_data, request=request)
        parsed = envelope.parsed

        return {
            "relevance_score": parsed.relevance_score,
            "ai_summary": parsed.post_meaning,
            "post_meaning": parsed.post_meaning,
            "seller_intent": parsed.seller_intent,
            "reliability_signals": parsed.reliability_signals,
            "pros": parsed.pros,
            "cons": parsed.cons,
            "warning_signs": parsed.warning_signs,
            "recommendation": parsed.recommendation,
            "image_product_match": parsed.image_product_match,
            "logic_notes": parsed.logic_notes,
            "raw_ai_response": envelope.raw_response_text,
            "raw_ai_response_data": envelope.raw_response_data,
            "ai_validation_errors": envelope.validation_errors,
            "ai_fallback_used": envelope.fallback_used,
            "ai_success": envelope.success,
        }
