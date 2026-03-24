from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class DuplicateSignal:
    is_duplicate: bool
    duplicate_key: str
    matched_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SellerSignal:
    seller_name: str
    quality: str
    indicators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommentSignal:
    positive_count: int = 0
    negative_count: int = 0
    indicators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LogicAnalysisResult:
    match_level: str
    logic_score: float
    completeness_score: float
    warning_flags: List[str] = field(default_factory=list)
    suspicious_indicators: List[str] = field(default_factory=list)
    duplicate: Dict[str, Any] = field(default_factory=dict)
    seller_signal: Dict[str, Any] = field(default_factory=dict)
    comment_signal: Dict[str, Any] = field(default_factory=dict)
    matched_terms: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    logic_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
