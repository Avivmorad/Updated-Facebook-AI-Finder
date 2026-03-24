from typing import Any, Dict, List

from app.models.scoring_models import ScoreCategories, ScoringResult
from config.scoring_config import ScoringPenalties, ScoringThresholds, ScoringWeights


class PostRanker:
    def __init__(self) -> None:
        self._weights = ScoringWeights()
        self._penalties_cfg = ScoringPenalties()
        self._thresholds = ScoringThresholds()

    def rank(self, analyzed_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []

        for item in analyzed_posts:
            scoring = self._score_post(item)

            ranked.append(
                {
                    **item,
                    "scoring": scoring.to_dict(),
                }
            )

        return sorted(
            ranked,
            key=lambda post: float(post.get("scoring", {}).get("final_score", 0.0)),
            reverse=True,
        )

    def _score_post(self, item: Dict[str, Any]) -> ScoringResult:
        logic = item.get("logic_analysis", {})
        ai = item.get("ai_analysis", {})

        categories = ScoreCategories(
            relevance=self._score_relevance(logic=logic, ai=ai),
            information_completeness=_clamp(_to_float(logic.get("completeness_score"), default=0.5)),
            suspicious_risk=self._score_suspicious_risk(logic=logic, ai=ai),
            seller_signal=self._score_seller(logic=logic),
            comments_signal=self._score_comments(logic=logic),
            ai_assessment=self._score_ai_assessment(ai=ai),
            image_product_match=self._score_image_match(ai=ai),
        )

        weighted = (
            categories.relevance * self._weights.relevance
            + categories.information_completeness * self._weights.information_completeness
            + categories.suspicious_risk * self._weights.suspicious_risk
            + categories.seller_signal * self._weights.seller_signal
            + categories.comments_signal * self._weights.comments_signal
            + categories.ai_assessment * self._weights.ai_assessment
            + categories.image_product_match * self._weights.image_product_match
        )

        penalties = self._collect_penalties(logic=logic, ai=ai)
        penalty_sum = sum(penalties.values())

        final_score = _clamp(round(weighted - penalty_sum, 4))

        recommendation_code = self._recommendation_code(final_score)
        recommendation_text = self._recommendation_text(recommendation_code, logic=logic, ai=ai)
        explanations = self._build_explanations(categories=categories, penalties=penalties, weighted=weighted)

        return ScoringResult(
            final_score=final_score,
            recommendation_code=recommendation_code,
            recommendation_text=recommendation_text,
            categories=categories,
            penalties=penalties,
            explanations=explanations,
        )

    def _score_relevance(self, logic: Dict[str, Any], ai: Dict[str, Any]) -> float:
        logic_score = _to_float(logic.get("logic_score"), default=0.5)
        ai_score = _to_float(ai.get("relevance_score"), default=0.5)
        return _clamp((logic_score * 0.6) + (ai_score * 0.4))

    def _score_suspicious_risk(self, logic: Dict[str, Any], ai: Dict[str, Any]) -> float:
        suspicious_count = len(_as_list(logic.get("suspicious_indicators")))
        warning_count = len(_as_list(logic.get("warning_flags")))
        ai_warning_count = len(_as_list(ai.get("warning_signs")))

        # Higher score means lower risk.
        risk = (suspicious_count * 0.16) + (warning_count * 0.08) + (ai_warning_count * 0.04)
        return _clamp(1.0 - risk)

    def _score_seller(self, logic: Dict[str, Any]) -> float:
        seller_signal = logic.get("seller_signal", {})
        quality = str(seller_signal.get("quality", "warning")).strip().lower()
        indicators = _as_list(seller_signal.get("indicators"))

        base = 1.0 if quality == "ok" else 0.65
        if "seller_name_missing" in indicators:
            base -= 0.25
        if "generic_seller_name" in indicators:
            base -= 0.20
        if "seller_name_too_short" in indicators:
            base -= 0.10

        return _clamp(base)

    def _score_comments(self, logic: Dict[str, Any]) -> float:
        comment_signal = logic.get("comment_signal", {})
        positive = _to_float(comment_signal.get("positive_count"), default=0.0)
        negative = _to_float(comment_signal.get("negative_count"), default=0.0)

        # Start neutral, increase with positive activity, reduce with negative signals.
        score = 0.5 + min(0.35, positive * 0.08) - min(0.45, negative * 0.15)
        return _clamp(score)

    def _score_ai_assessment(self, ai: Dict[str, Any]) -> float:
        recommendation = str(ai.get("recommendation", "consider")).strip().lower()
        relevance = _to_float(ai.get("relevance_score"), default=0.5)

        rec_score_map = {
            "buy": 0.95,
            "consider": 0.65,
            "skip": 0.25,
        }
        rec_score = rec_score_map.get(recommendation, 0.55)

        return _clamp((relevance * 0.55) + (rec_score * 0.45))

    def _score_image_match(self, ai: Dict[str, Any]) -> float:
        match_value = str(ai.get("image_product_match", "unclear")).strip().lower()
        match_score = {
            "match": 1.0,
            "unclear": 0.55,
            "mismatch": 0.15,
        }.get(match_value, 0.55)
        return _clamp(match_score)

    def _collect_penalties(self, logic: Dict[str, Any], ai: Dict[str, Any]) -> Dict[str, float]:
        penalties: Dict[str, float] = {}

        duplicate = bool(logic.get("duplicate", {}).get("is_duplicate", False))
        if duplicate:
            penalties["duplicate"] = self._penalties_cfg.duplicate

        warning_flags = set(_as_list(logic.get("warning_flags")))
        if "out_of_price_range" in warning_flags:
            penalties["out_of_price_range"] = self._penalties_cfg.out_of_price_range
        if "missing_required_image" in warning_flags:
            penalties["missing_required_image"] = self._penalties_cfg.missing_required_image

        if bool(ai.get("ai_fallback_used", False)):
            penalties["ai_fallback"] = self._penalties_cfg.ai_fallback

        return penalties

    def _recommendation_code(self, final_score: float) -> str:
        if final_score >= self._thresholds.recommended:
            return "RECOMMENDED"
        if final_score >= self._thresholds.consider:
            return "CONSIDER"
        if final_score >= self._thresholds.review:
            return "REVIEW"
        return "SKIP"

    def _recommendation_text(self, code: str, logic: Dict[str, Any], ai: Dict[str, Any]) -> str:
        if code == "RECOMMENDED":
            return "Strong overall match with low risk signals."
        if code == "CONSIDER":
            return "Potentially good option; review key details before deciding."
        if code == "REVIEW":
            warnings = ", ".join(_as_list(logic.get("warning_flags"))[:3])
            return f"Needs manual review due to warning signals: {warnings or 'mixed quality indicators'}."

        ai_warning = ", ".join(_as_list(ai.get("warning_signs"))[:3])
        return f"Low confidence candidate. Primary concerns: {ai_warning or 'risk/quality penalties'}"

    def _build_explanations(
        self,
        categories: ScoreCategories,
        penalties: Dict[str, float],
        weighted: float,
    ) -> List[str]:
        explanations = [
            f"category.relevance={categories.relevance:.3f} (w={self._weights.relevance:.2f})",
            (
                "category.information_completeness="
                + f"{categories.information_completeness:.3f} (w={self._weights.information_completeness:.2f})"
            ),
            f"category.suspicious_risk={categories.suspicious_risk:.3f} (w={self._weights.suspicious_risk:.2f})",
            f"category.seller_signal={categories.seller_signal:.3f} (w={self._weights.seller_signal:.2f})",
            f"category.comments_signal={categories.comments_signal:.3f} (w={self._weights.comments_signal:.2f})",
            f"category.ai_assessment={categories.ai_assessment:.3f} (w={self._weights.ai_assessment:.2f})",
            (
                "category.image_product_match="
                + f"{categories.image_product_match:.3f} (w={self._weights.image_product_match:.2f})"
            ),
            f"weighted_score_before_penalties={weighted:.4f}",
        ]

        if penalties:
            for name, value in penalties.items():
                explanations.append(f"penalty.{name}=-{value:.3f}")
        else:
            explanations.append("penalty.none")

        return explanations


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    output: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            output.append(text)
    return output


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))
