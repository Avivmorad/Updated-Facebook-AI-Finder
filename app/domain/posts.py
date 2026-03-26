from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CollectedPost:
    post_link: str
    post_text: str = ""
    images: List[str] = field(default_factory=list)
    publish_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidatePostRef:
    post_id: str
    post_link: str
    preview_text: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchExecutionResult:
    items: List[CandidatePostRef] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fatal_error: Optional[str] = None
    attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "warnings": list(self.warnings),
            "fatal_error": self.fatal_error,
            "attempts": self.attempts,
        }


@dataclass
class PostExtractionResult:
    reference: Dict[str, Any]
    raw_post_data: Dict[str, Any] = field(default_factory=dict)
    normalized_post_data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
