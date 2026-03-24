from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass(frozen=True)
class LogicAnalysisConfig:
    suspicious_words: Set[str] = field(
        default_factory=lambda: {
            "urgent",
            "only today",
            "cash only",
            "no questions",
            "deposit",
            "bank transfer only",
            "bitcoins",
            "crypto",
            "wire transfer",
            "no returns",
            "first come first served",
            "scam",
            "fake",
            "replica",
        }
    )
    positive_comment_markers: Set[str] = field(
        default_factory=lambda: {
            "available",
            "still available",
            "thanks",
            "recommend",
            "good",
            "legit",
            "working",
        }
    )
    negative_comment_markers: Set[str] = field(
        default_factory=lambda: {
            "scam",
            "fake",
            "not as described",
            "broken",
            "fraud",
            "warning",
            "avoid",
        }
    )
    missing_field_penalties: Dict[str, float] = field(
        default_factory=lambda: {
            "title": 0.20,
            "description": 0.15,
            "price": 0.20,
            "location": 0.10,
            "images": 0.20,
            "seller_name": 0.15,
        }
    )
    suspicious_word_penalty_per_word: float = 0.08
    duplicate_penalty: float = 0.35
    seller_generic_name_penalty: float = 0.10
    seller_short_name_penalty: float = 0.08
    negative_comments_penalty: float = 0.15
    weak_match_threshold: float = 0.40
    partial_match_threshold: float = 0.70
