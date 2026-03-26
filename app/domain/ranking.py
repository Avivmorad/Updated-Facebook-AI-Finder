from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RankedMatch:
    rank: int
    match_score: float
    post: Dict[str, Any]
    ai_match: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
