from app.scoring.ranker import PostRanker, _to_float, _as_list, _clamp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post(
    logic_score: float = 0.7,
    completeness: float = 0.7,
    ai_relevance: float = 0.7,
    ai_recommendation: str = "consider",
    ai_image_match: str = "unclear",
    suspicious_indicators: list | None = None,
    warning_flags: list | None = None,
    ai_warning_signs: list | None = None,
    seller_quality: str = "ok",
    seller_indicators: list | None = None,
    positive_comments: int = 0,
    negative_comments: int = 0,
    is_duplicate: bool = False,
    ai_fallback: bool = False,
) -> dict:
    return {
        "logic_analysis": {
            "logic_score": logic_score,
            "completeness_score": completeness,
            "suspicious_indicators": suspicious_indicators or [],
            "warning_flags": warning_flags or [],
            "duplicate": {"is_duplicate": is_duplicate},
            "seller_signal": {
                "quality": seller_quality,
                "indicators": seller_indicators or [],
            },
            "comment_signal": {
                "positive_count": positive_comments,
                "negative_count": negative_comments,
            },
        },
        "ai_analysis": {
            "relevance_score": ai_relevance,
            "recommendation": ai_recommendation,
            "image_product_match": ai_image_match,
            "warning_signs": ai_warning_signs or [],
            "ai_fallback_used": ai_fallback,
        },
    }


# ---------------------------------------------------------------------------
# rank() — sorting and structure
# ---------------------------------------------------------------------------


class TestRankOrdering:
    def test_returns_list_of_dicts(self):
        ranker = PostRanker()
        result = ranker.rank([_post(logic_score=0.8)])
        assert isinstance(result, list)
        assert isinstance(result[0], dict)

    def test_each_result_has_scoring_key(self):
        ranker = PostRanker()
        result = ranker.rank([_post()])
        assert "scoring" in result[0]

    def test_sorted_descending_by_final_score(self):
        ranker = PostRanker()
        posts = [
            _post(logic_score=0.2, ai_relevance=0.2, completeness=0.2),
            _post(logic_score=0.9, ai_relevance=0.9, completeness=0.9),
            _post(logic_score=0.5, ai_relevance=0.5, completeness=0.5),
        ]
        result = ranker.rank(posts)
        scores = [r["scoring"]["final_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_list_returns_empty_list(self):
        ranker = PostRanker()
        assert ranker.rank([]) == []

    def test_original_fields_preserved(self):
        ranker = PostRanker()
        post = {**_post(), "post_id": "abc123", "title": "iPhone"}
        result = ranker.rank([post])
        assert result[0]["post_id"] == "abc123"
        assert result[0]["title"] == "iPhone"


# ---------------------------------------------------------------------------
# scoring structure
# ---------------------------------------------------------------------------


class TestScoringStructure:
    def test_scoring_dict_has_expected_keys(self):
        ranker = PostRanker()
        scoring = ranker.rank([_post()])[0]["scoring"]
        assert "final_score" in scoring
        assert "recommendation_code" in scoring
        assert "recommendation_text" in scoring
        assert "categories" in scoring
        assert "penalties" in scoring
        assert "explanations" in scoring

    def test_final_score_is_between_0_and_1(self):
        ranker = PostRanker()
        result = ranker.rank([_post()])[0]["scoring"]
        assert 0.0 <= result["final_score"] <= 1.0

    def test_categories_all_clamped(self):
        ranker = PostRanker()
        cats = ranker.rank([_post()])[0]["scoring"]["categories"]
        for key, value in cats.items():
            assert 0.0 <= value <= 1.0, f"Category '{key}' out of range: {value}"


# ---------------------------------------------------------------------------
# recommendation codes
# ---------------------------------------------------------------------------


class TestRecommendationCodes:
    def test_high_score_gives_recommended(self):
        ranker = PostRanker()
        post = _post(
            logic_score=0.99,
            ai_relevance=0.99,
            completeness=0.99,
            ai_recommendation="buy",
            ai_image_match="match",
        )
        result = ranker.rank([post])[0]["scoring"]
        assert result["recommendation_code"] == "RECOMMENDED"

    def test_mid_score_gives_consider(self):
        ranker = PostRanker()
        post = _post(logic_score=0.55, ai_relevance=0.55, completeness=0.55)
        result = ranker.rank([post])[0]["scoring"]
        code = result["recommendation_code"]
        assert code in ("CONSIDER", "REVIEW", "SKIP")

    def test_low_score_gives_skip(self):
        ranker = PostRanker()
        post = _post(
            logic_score=0.1,
            ai_relevance=0.1,
            completeness=0.1,
            ai_recommendation="skip",
            suspicious_indicators=["s1", "s2", "s3", "s4", "s5"],
            warning_flags=["w1", "w2", "w3"],
            ai_warning_signs=["a1", "a2"],
            is_duplicate=True,
        )
        result = ranker.rank([post])[0]["scoring"]
        assert result["recommendation_code"] == "SKIP"

    def test_recommendation_text_not_empty(self):
        ranker = PostRanker()
        result = ranker.rank([_post()])[0]["scoring"]
        assert isinstance(result["recommendation_text"], str)
        assert len(result["recommendation_text"]) > 0


# ---------------------------------------------------------------------------
# penalties
# ---------------------------------------------------------------------------


class TestPenalties:
    def test_no_penalties_when_clean(self):
        ranker = PostRanker()
        result = ranker.rank([_post()])[0]["scoring"]
        assert result["penalties"] == {}

    def test_duplicate_penalty_applied(self):
        ranker = PostRanker()
        result = ranker.rank([_post(is_duplicate=True)])[0]["scoring"]
        assert "duplicate" in result["penalties"]

    def test_ai_fallback_penalty_applied(self):
        ranker = PostRanker()
        result = ranker.rank([_post(ai_fallback=True)])[0]["scoring"]
        assert "ai_fallback" in result["penalties"]

    def test_out_of_price_range_penalty_applied(self):
        ranker = PostRanker()
        result = ranker.rank([_post(warning_flags=["out_of_price_range"])])[0][
            "scoring"
        ]
        assert "out_of_price_range" in result["penalties"]

    def test_missing_image_penalty_applied(self):
        ranker = PostRanker()
        result = ranker.rank([_post(warning_flags=["missing_required_image"])])[0][
            "scoring"
        ]
        assert "missing_required_image" in result["penalties"]

    def test_penalty_lowers_score_below_no_penalty(self):
        ranker = PostRanker()
        clean = ranker.rank([_post()])[0]["scoring"]["final_score"]
        penalised = ranker.rank([_post(is_duplicate=True)])[0]["scoring"]["final_score"]
        assert penalised < clean


# ---------------------------------------------------------------------------
# seller scoring
# ---------------------------------------------------------------------------


class TestSellerScoring:
    def test_ok_seller_quality_higher_than_warning(self):
        ranker = PostRanker()
        ok_post = _post(seller_quality="ok")
        warn_post = _post(seller_quality="warning")
        ok_score = ranker.rank([ok_post])[0]["scoring"]["categories"]["seller_signal"]
        warn_score = ranker.rank([warn_post])[0]["scoring"]["categories"][
            "seller_signal"
        ]
        assert ok_score > warn_score

    def test_seller_name_missing_reduces_score(self):
        ranker = PostRanker()
        clean = _post(seller_quality="ok", seller_indicators=[])
        no_name = _post(seller_quality="ok", seller_indicators=["seller_name_missing"])
        s_clean = ranker.rank([clean])[0]["scoring"]["categories"]["seller_signal"]
        s_no_name = ranker.rank([no_name])[0]["scoring"]["categories"]["seller_signal"]
        assert s_no_name < s_clean


# ---------------------------------------------------------------------------
# comments signal
# ---------------------------------------------------------------------------


class TestCommentsSignal:
    def test_positive_comments_increase_signal(self):
        ranker = PostRanker()
        base = ranker.rank([_post(positive_comments=0)])[0]["scoring"]["categories"][
            "comments_signal"
        ]
        high = ranker.rank([_post(positive_comments=5)])[0]["scoring"]["categories"][
            "comments_signal"
        ]
        assert high > base

    def test_negative_comments_decrease_signal(self):
        ranker = PostRanker()
        base = ranker.rank([_post(negative_comments=0)])[0]["scoring"]["categories"][
            "comments_signal"
        ]
        bad = ranker.rank([_post(negative_comments=5)])[0]["scoring"]["categories"][
            "comments_signal"
        ]
        assert bad < base

    def test_signal_clamped_below_1(self):
        ranker = PostRanker()
        result = ranker.rank([_post(positive_comments=100)])[0]["scoring"][
            "categories"
        ]["comments_signal"]
        assert result <= 1.0

    def test_signal_clamped_above_0(self):
        ranker = PostRanker()
        result = ranker.rank([_post(negative_comments=100)])[0]["scoring"][
            "categories"
        ]["comments_signal"]
        assert result >= 0.0


# ---------------------------------------------------------------------------
# explanations
# ---------------------------------------------------------------------------


class TestExplanations:
    def test_explanations_list_not_empty(self):
        ranker = PostRanker()
        explanations = ranker.rank([_post()])[0]["scoring"]["explanations"]
        assert isinstance(explanations, list)
        assert len(explanations) > 0

    def test_weighted_score_in_explanations(self):
        ranker = PostRanker()
        explanations = ranker.rank([_post()])[0]["scoring"]["explanations"]
        assert any("weighted_score_before_penalties" in e for e in explanations)

    def test_no_penalties_explanation_shown(self):
        ranker = PostRanker()
        explanations = ranker.rank([_post()])[0]["scoring"]["explanations"]
        assert any("penalty.none" in e for e in explanations)

    def test_penalty_names_in_explanations(self):
        ranker = PostRanker()
        explanations = ranker.rank([_post(is_duplicate=True)])[0]["scoring"][
            "explanations"
        ]
        assert any("penalty.duplicate" in e for e in explanations)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


class TestUtilFunctions:
    def test_to_float_converts_int(self):
        assert _to_float(5) == 5.0

    def test_to_float_converts_string(self):
        assert _to_float("0.75") == 0.75

    def test_to_float_returns_default_for_none(self):
        assert _to_float(None, default=0.5) == 0.5

    def test_to_float_returns_default_for_invalid_string(self):
        assert _to_float("abc", default=0.3) == 0.3

    def test_as_list_returns_list_of_strings(self):
        assert _as_list(["a", "b"]) == ["a", "b"]

    def test_as_list_returns_empty_for_non_list(self):
        assert _as_list("not a list") == []

    def test_as_list_filters_empty_items(self):
        assert _as_list(["a", "", "  "]) == ["a"]

    def test_clamp_clamps_to_0_1(self):
        assert _clamp(-0.5) == 0.0
        assert _clamp(1.5) == 1.0
        assert _clamp(0.5) == 0.5

    def test_clamp_custom_bounds(self):
        assert _clamp(0.5, min_value=0.6, max_value=1.0) == 0.6
        assert _clamp(1.5, min_value=0.0, max_value=1.2) == 1.2
