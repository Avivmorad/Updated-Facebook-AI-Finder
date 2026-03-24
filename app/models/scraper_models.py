from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RawSearchResultRef:
    post_id: str
    title: str
    url: str
    snippet: str
    price_text: Optional[str] = None
    region: Optional[str] = None
    source_platform: str = "facebook_marketplace"
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchExecutionResult:
    items: List[RawSearchResultRef] = field(default_factory=list)
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
