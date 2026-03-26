from typing import Any, Dict, List

from app.domain.ranking import RankedMatch


class PostRanker:
    def rank(self, relevant_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sorted_posts = sorted(
            relevant_posts,
            key=lambda item: _clamp_score(_to_float(_to_dict(item.get("ai_match")).get("match_score"), default=0.0)),
            reverse=True,
        )

        ranked: List[Dict[str, Any]] = []
        for rank, item in enumerate(sorted_posts, start=1):
            ai_match = _to_dict(item.get("ai_match"))
            ranked_match = RankedMatch(
                rank=rank,
                match_score=_clamp_score(_to_float(ai_match.get("match_score"), default=0.0)),
                post=_to_dict(item.get("post")),
                ai_match=ai_match,
            )
            ranked.append(ranked_match.to_dict())

        return ranked


def _to_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))
