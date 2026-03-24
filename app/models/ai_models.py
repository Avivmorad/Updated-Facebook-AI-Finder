from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AIParsedAnalysis:
    post_meaning: str
    seller_intent: str
    reliability_signals: List[str] = field(default_factory=list)
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    warning_signs: List[str] = field(default_factory=list)
    recommendation: str = "consider"
    image_product_match: str = "unclear"
    logic_notes: str = ""
    relevance_score: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AIAnalysisEnvelope:
    parsed: AIParsedAnalysis
    raw_response_text: str = ""
    raw_response_data: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    fallback_used: bool = False
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parsed": self.parsed.to_dict(),
            "raw_response_text": self.raw_response_text,
            "raw_response_data": dict(self.raw_response_data),
            "validation_errors": list(self.validation_errors),
            "fallback_used": self.fallback_used,
            "success": self.success,
        }


@dataclass
class AIPromptPacket:
    system_prompt: str
    user_prompt: str
    expected_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AIRequestPayload:
    product_query: str
    post_title: str
    post_text: str
    price: Optional[float]
    location: str
    seller_name: str
    comments: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
