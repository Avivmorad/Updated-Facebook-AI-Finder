import re
from typing import Any, Dict, List, Set

from app.models.logic_models import CommentSignal, DuplicateSignal, LogicAnalysisResult, SellerSignal
from app.models.input_models import SearchRequest
from config.logic_analysis_config import LogicAnalysisConfig


class LogicAnalyzer:
    def __init__(self, config: LogicAnalysisConfig | None = None) -> None:
        self._config = config or LogicAnalysisConfig()
        self._seen_exact_keys: Set[str] = set()
        self._seen_soft_keys: Set[str] = set()

    def reset_session(self) -> None:
        self._seen_exact_keys.clear()
        self._seen_soft_keys.clear()

    def analyze(self, post_data: Dict[str, Any], request: SearchRequest) -> Dict[str, Any]:
        normalized = post_data.get("normalized_post_data", {})

        title = _text_or_empty(normalized.get("title") or post_data.get("title"))
        description = _text_or_empty(normalized.get("text") or post_data.get("description"))
        seller_name = _text_or_empty(normalized.get("seller_name") or post_data.get("seller_name"))
        location = _text_or_empty(normalized.get("location") or post_data.get("region"))
        price = _safe_float(normalized.get("price", post_data.get("price")))
        images = _list_or_empty(normalized.get("images", post_data.get("images", [])))
        comments = _list_or_empty(normalized.get("comments", post_data.get("comments", [])))
        signals = _list_or_empty(
            normalized.get("important_visible_signals", post_data.get("important_visible_signals", []))
        )

        combined_text = " ".join([title, description, " ".join(signals)]).strip().lower()
        matched_terms = self._find_matched_terms(combined_text, request)

        in_price_range = self._is_in_price_range(price, request)
        has_required_image = (not request.require_image) or bool(images)

        duplicate_signal = self._duplicate_signal(
            title=title,
            seller_name=seller_name,
            price=price,
            location=location,
        )
        suspicious_indicators = self._suspicious_indicators(combined_text)
        seller_signal = self._analyze_seller_name(seller_name)
        comment_signal = self._analyze_comments(comments)
        missing_fields = self._missing_fields(
            title=title,
            description=description,
            price=price,
            location=location,
            images=images,
            seller_name=seller_name,
        )

        completeness_score = self._completeness_score(missing_fields)
        relevance_score = self._relevance_score(matched_terms, request, title, description)

        penalty = 0.0
        warning_flags: List[str] = []

        if not in_price_range:
            penalty += 0.20
            warning_flags.append("out_of_price_range")
        if not has_required_image:
            penalty += 0.20
            warning_flags.append("missing_required_image")
        if duplicate_signal.is_duplicate:
            penalty += self._config.duplicate_penalty
            warning_flags.append("possible_duplicate")

        penalty += self._config.suspicious_word_penalty_per_word * len(suspicious_indicators)

        if seller_signal.quality != "ok":
            warning_flags.append("seller_name_quality_issue")
            if "generic_seller_name" in seller_signal.indicators:
                penalty += self._config.seller_generic_name_penalty
            if "seller_name_too_short" in seller_signal.indicators:
                penalty += self._config.seller_short_name_penalty

        if comment_signal.negative_count > 0:
            penalty += self._config.negative_comments_penalty
            warning_flags.append("negative_comment_signal")

        base_score = (relevance_score * 0.55) + (completeness_score * 0.45)
        logic_score = max(0.0, min(1.0, round(base_score - penalty, 4)))

        match_level = self._match_level(logic_score)
        logic_summary = self._build_summary(
            match_level=match_level,
            matched_terms=matched_terms,
            warning_flags=warning_flags,
            suspicious_indicators=suspicious_indicators,
            missing_fields=missing_fields,
        )

        result = LogicAnalysisResult(
            match_level=match_level,
            logic_score=logic_score,
            completeness_score=round(completeness_score, 4),
            warning_flags=warning_flags,
            suspicious_indicators=suspicious_indicators,
            duplicate=duplicate_signal.to_dict(),
            seller_signal=seller_signal.to_dict(),
            comment_signal=comment_signal.to_dict(),
            matched_terms=matched_terms,
            missing_fields=missing_fields,
            logic_summary=logic_summary,
        )

        result_dict = result.to_dict()
        result_dict["in_price_range"] = in_price_range
        result_dict["has_required_image"] = has_required_image
        return result_dict

    def _find_matched_terms(self, text: str, request: SearchRequest) -> List[str]:
        candidates = [request.query_text] + list(request.tags) + list(request.secondary_attributes)
        matched: List[str] = []
        for term in candidates:
            clean = term.strip().lower()
            if clean and clean in text:
                matched.append(clean)
        return sorted(set(matched))

    def _is_in_price_range(self, price: float | None, request: SearchRequest) -> bool:
        if price is None:
            return True
        if request.min_price is not None and price < request.min_price:
            return False
        if request.max_price is not None and price > request.max_price:
            return False
        return True

    def _duplicate_signal(self, title: str, seller_name: str, price: float | None, location: str) -> DuplicateSignal:
        base_title = _normalize_key(title)
        base_seller = _normalize_key(seller_name)
        base_location = _normalize_key(location)
        price_key = "na" if price is None else str(round(price, 2))

        exact_key = f"{base_title}|{base_seller}|{price_key}"
        soft_key = f"{base_title}|{base_location}"

        matched_keys: List[str] = []
        is_duplicate = False
        if exact_key in self._seen_exact_keys:
            is_duplicate = True
            matched_keys.append("exact")
        if soft_key in self._seen_soft_keys:
            is_duplicate = True
            matched_keys.append("soft")

        self._seen_exact_keys.add(exact_key)
        self._seen_soft_keys.add(soft_key)

        return DuplicateSignal(
            is_duplicate=is_duplicate,
            duplicate_key=exact_key,
            matched_keys=matched_keys,
        )

    def _suspicious_indicators(self, combined_text: str) -> List[str]:
        hits: List[str] = []
        for word in sorted(self._config.suspicious_words):
            if word in combined_text:
                hits.append(word)
        return hits

    def _analyze_seller_name(self, seller_name: str) -> SellerSignal:
        indicators: List[str] = []
        lowered = seller_name.lower().strip()

        if not lowered:
            indicators.append("seller_name_missing")
        elif lowered in {"seller", "user", "facebook user", "unknown"}:
            indicators.append("generic_seller_name")

        tokens = [token for token in re.split(r"\s+", lowered) if token]
        if lowered and len("".join(tokens)) < 3:
            indicators.append("seller_name_too_short")

        quality = "ok" if not indicators else "warning"
        return SellerSignal(seller_name=seller_name, quality=quality, indicators=indicators)

    def _analyze_comments(self, comments: List[str]) -> CommentSignal:
        positive = 0
        negative = 0
        indicators: List[str] = []

        for comment in comments:
            lowered = comment.lower()
            if any(marker in lowered for marker in self._config.positive_comment_markers):
                positive += 1
            if any(marker in lowered for marker in self._config.negative_comment_markers):
                negative += 1

        if positive > 0:
            indicators.append("positive_comment_activity")
        if negative > 0:
            indicators.append("negative_comment_activity")

        return CommentSignal(
            positive_count=positive,
            negative_count=negative,
            indicators=indicators,
        )

    def _missing_fields(
        self,
        title: str,
        description: str,
        price: float | None,
        location: str,
        images: List[str],
        seller_name: str,
    ) -> List[str]:
        missing: List[str] = []
        if not title:
            missing.append("title")
        if not description:
            missing.append("description")
        if price is None:
            missing.append("price")
        if not location:
            missing.append("location")
        if not images:
            missing.append("images")
        if not seller_name:
            missing.append("seller_name")
        return missing

    def _completeness_score(self, missing_fields: List[str]) -> float:
        score = 1.0
        for field in missing_fields:
            score -= self._config.missing_field_penalties.get(field, 0.0)
        return max(0.0, min(1.0, score))

    def _relevance_score(
        self,
        matched_terms: List[str],
        request: SearchRequest,
        title: str,
        description: str,
    ) -> float:
        candidate_terms = [request.query_text] + list(request.tags) + list(request.secondary_attributes)
        candidate_terms = [term.strip().lower() for term in candidate_terms if term and term.strip()]
        if not candidate_terms:
            return 0.5

        coverage = len(matched_terms) / len(set(candidate_terms))
        title_bonus = 0.2 if request.query_text.lower() in title.lower() else 0.0
        desc_bonus = 0.1 if request.query_text.lower() in description.lower() else 0.0

        return max(0.0, min(1.0, coverage + title_bonus + desc_bonus))

    def _match_level(self, logic_score: float) -> str:
        if logic_score >= self._config.partial_match_threshold:
            return "matched"
        if logic_score >= self._config.weak_match_threshold:
            return "partially_matched"
        return "weak_match"

    def _build_summary(
        self,
        match_level: str,
        matched_terms: List[str],
        warning_flags: List[str],
        suspicious_indicators: List[str],
        missing_fields: List[str],
    ) -> str:
        parts = [f"match={match_level}"]
        if matched_terms:
            parts.append("matched_terms=" + ",".join(matched_terms[:5]))
        if warning_flags:
            parts.append("warnings=" + ",".join(warning_flags[:5]))
        if suspicious_indicators:
            parts.append("suspicious=" + ",".join(suspicious_indicators[:5]))
        if missing_fields:
            parts.append("missing=" + ",".join(missing_fields[:5]))
        return " | ".join(parts)


def _text_or_empty(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _list_or_empty(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    output: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            output.append(text)
    return output


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
