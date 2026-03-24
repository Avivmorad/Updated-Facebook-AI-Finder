from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


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
