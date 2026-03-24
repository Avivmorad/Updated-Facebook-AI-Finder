from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class ScoreCategories:
    relevance: float
    information_completeness: float
    suspicious_risk: float
    seller_signal: float
    comments_signal: float
    ai_assessment: float
    image_product_match: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class ScoringResult:
    final_score: float
    recommendation_code: str
    recommendation_text: str
    categories: ScoreCategories
    penalties: Dict[str, float] = field(default_factory=dict)
    explanations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_score": self.final_score,
            "recommendation_code": self.recommendation_code,
            "recommendation_text": self.recommendation_text,
            "categories": self.categories.to_dict(),
            "penalties": dict(self.penalties),
            "explanations": list(self.explanations),
        }
