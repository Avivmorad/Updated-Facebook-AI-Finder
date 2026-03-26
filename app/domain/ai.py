from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AIMatchResult:
    is_relevant: bool
    match_score: float
    detected_item: str
    match_reason: str
    confidence: float
    is_recent_24h: bool
    publish_date_observed: str
    publish_date_reason: str
    publish_date_confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AIAnalysisEnvelope:
    result: Optional[AIMatchResult]
    raw_response_text: str = ""
    raw_response_data: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.to_dict() if self.result is not None else None,
            "raw_response_text": self.raw_response_text,
            "raw_response_data": dict(self.raw_response_data),
            "validation_errors": list(self.validation_errors),
            "success": self.success,
        }


@dataclass(frozen=True)
class AIPromptPacket:
    system_prompt: str
    user_prompt: str
    expected_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AIRequestPayload:
    query: str
    post_text: str
    image_urls: List[str] = field(default_factory=list)
    publish_date_text: str = ""
    parser_time_reason: str = ""
    post_screenshot_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
