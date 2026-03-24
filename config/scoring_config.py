from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    relevance: float = 0.24
    information_completeness: float = 0.16
    suspicious_risk: float = 0.14
    seller_signal: float = 0.12
    comments_signal: float = 0.10
    ai_assessment: float = 0.14
    image_product_match: float = 0.10


@dataclass(frozen=True)
class ScoringPenalties:
    duplicate: float = 0.20
    out_of_price_range: float = 0.15
    missing_required_image: float = 0.12
    ai_fallback: float = 0.06


@dataclass(frozen=True)
class ScoringThresholds:
    recommended: float = 0.78
    consider: float = 0.58
    review: float = 0.40
