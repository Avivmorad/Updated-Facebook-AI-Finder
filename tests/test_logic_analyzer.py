from app.logic.logic_analyzer import (
    LogicAnalyzer,
    _text_or_empty,
    _list_or_empty,
    _safe_float,
    _normalize_key,
)
from app.models.input_models import SearchRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    query_text: str = "iPhone",
    tags: list | None = None,
    secondary_attributes: list | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    require_image: bool = False,
    is_free: bool = False,
) -> SearchRequest:
    return SearchRequest(
        query_text=query_text,
        tags=tags or [],
        secondary_attributes=secondary_attributes or [],
        forbidden_words=[],
        min_price=min_price,
        max_price=max_price,
        is_free=is_free,
        post_age="24h",
        require_image=require_image,
        language="he",
        target_regions=[],
        all_country=True,
        group_mode="all_groups",
        groups=[],
        group_sources=["user_groups"],
        group_urls=[],
        select_all_groups=False,
    )


def _make_post(
    title: str = "iPhone 13",
    description: str = "Great condition",
    price: float | None = 2000.0,
    seller_name: str = "Alice",
    location: str = "Tel Aviv",
    images: list | None = None,
    comments: list | None = None,
    signals: list | None = None,
) -> dict:
    return {
        "normalized_post_data": {
            "title": title,
            "text": description,
            "price": price,
            "seller_name": seller_name,
            "location": location,
            "images": images if images is not None else ["img.jpg"],
            "comments": comments if comments is not None else [],
            "important_visible_signals": signals or [],
        }
    }


# ---------------------------------------------------------------------------
# analyze() — output structure
# ---------------------------------------------------------------------------


class TestAnalyzeOutputStructure:
    def test_returns_dict_with_required_keys(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(), _make_request())
        for key in [
            "logic_score",
            "match_level",
            "completeness_score",
            "warning_flags",
            "suspicious_indicators",
            "duplicate",
            "seller_signal",
            "comment_signal",
            "matched_terms",
            "missing_fields",
            "logic_summary",
            "in_price_range",
            "has_required_image",
        ]:
            assert key in result, f"Missing key: {key}"

    def test_logic_score_between_0_and_1(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(), _make_request())
        assert 0.0 <= result["logic_score"] <= 1.0

    def test_completeness_score_between_0_and_1(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(), _make_request())
        assert 0.0 <= result["completeness_score"] <= 1.0


# ---------------------------------------------------------------------------
# Relevance / matched terms
# ---------------------------------------------------------------------------


class TestRelevance:
    def test_query_text_in_title_gives_high_relevance(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(title="iPhone 13 Pro"),
            _make_request(query_text="iphone"),
        )
        assert "iphone" in result["matched_terms"]
        assert result["logic_score"] > 0.5

    def test_no_match_returns_low_relevance(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(title="Samsung Galaxy"),
            _make_request(query_text="iphone"),
        )
        assert "iphone" not in result["matched_terms"]

    def test_tags_are_matched_in_combined_text(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(title="Apple laptop silver"),
            _make_request(query_text="laptop", tags=["silver"]),
        )
        assert "silver" in result["matched_terms"]
        assert "laptop" in result["matched_terms"]


# ---------------------------------------------------------------------------
# Price range validation
# ---------------------------------------------------------------------------


class TestPriceRange:
    def test_price_in_range_is_valid(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(price=500.0),
            _make_request(min_price=100.0, max_price=1000.0),
        )
        assert result["in_price_range"] is True
        assert "out_of_price_range" not in result["warning_flags"]

    def test_price_below_min_is_out_of_range(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(price=50.0),
            _make_request(min_price=100.0),
        )
        assert result["in_price_range"] is False
        assert "out_of_price_range" in result["warning_flags"]

    def test_price_above_max_is_out_of_range(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(price=2000.0),
            _make_request(max_price=1000.0),
        )
        assert result["in_price_range"] is False

    def test_none_price_is_always_in_range(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(price=None),
            _make_request(min_price=100.0, max_price=500.0),
        )
        assert result["in_price_range"] is True

    def test_no_price_constraints_always_in_range(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(price=9999.0),
            _make_request(),
        )
        assert result["in_price_range"] is True


# ---------------------------------------------------------------------------
# Image requirement
# ---------------------------------------------------------------------------


class TestImageRequirement:
    def test_image_not_required_always_satisfied(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(images=[]),
            _make_request(require_image=False),
        )
        assert result["has_required_image"] is True
        assert "missing_required_image" not in result["warning_flags"]

    def test_image_required_and_present_is_satisfied(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(images=["photo.jpg"]),
            _make_request(require_image=True),
        )
        assert result["has_required_image"] is True

    def test_image_required_but_missing_triggers_warning(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(images=[]),
            _make_request(require_image=True),
        )
        assert result["has_required_image"] is False
        assert "missing_required_image" in result["warning_flags"]


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    def test_first_post_is_not_duplicate(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(), _make_request())
        assert result["duplicate"]["is_duplicate"] is False

    def test_second_identical_post_is_duplicate(self):
        analyzer = LogicAnalyzer()
        post = _make_post(title="iPhone 13", seller_name="Alice", price=2000.0)
        request = _make_request()
        analyzer.analyze(post, request)
        result2 = analyzer.analyze(post, request)
        assert result2["duplicate"]["is_duplicate"] is True
        assert "possible_duplicate" in result2["warning_flags"]

    def test_reset_session_clears_duplicates(self):
        analyzer = LogicAnalyzer()
        post = _make_post()
        request = _make_request()
        analyzer.analyze(post, request)
        analyzer.reset_session()
        result = analyzer.analyze(post, request)
        assert result["duplicate"]["is_duplicate"] is False


# ---------------------------------------------------------------------------
# Suspicious indicators
# ---------------------------------------------------------------------------


class TestSuspiciousIndicators:
    def test_suspicious_word_detected(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(title="Urgent sale, cash only, no questions"),
            _make_request(),
        )
        assert len(result["suspicious_indicators"]) >= 1

    def test_clean_post_has_no_suspicious_indicators(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(title="iPhone 13 great condition"),
            _make_request(),
        )
        assert result["suspicious_indicators"] == []


# ---------------------------------------------------------------------------
# Seller signal analysis
# ---------------------------------------------------------------------------


class TestSellerSignal:
    def test_normal_seller_name_is_ok(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(seller_name="John Smith"), _make_request())
        assert result["seller_signal"]["quality"] == "ok"

    def test_missing_seller_name_triggers_warning(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(seller_name=""), _make_request())
        assert result["seller_signal"]["quality"] == "warning"
        assert "seller_name_missing" in result["seller_signal"]["indicators"]

    def test_generic_seller_name_triggers_warning(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(seller_name="seller"), _make_request())
        assert result["seller_signal"]["quality"] == "warning"
        assert "generic_seller_name" in result["seller_signal"]["indicators"]

    def test_short_seller_name_triggers_warning(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(seller_name="AB"), _make_request())
        assert result["seller_signal"]["quality"] == "warning"
        assert "seller_name_too_short" in result["seller_signal"]["indicators"]


# ---------------------------------------------------------------------------
# Comment signal analysis
# ---------------------------------------------------------------------------


class TestCommentSignal:
    def test_no_comments_gives_neutral_signal(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(comments=[]), _make_request())
        assert result["comment_signal"]["positive_count"] == 0
        assert result["comment_signal"]["negative_count"] == 0

    def test_positive_comment_counted(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(comments=["Still available, thanks!"]),
            _make_request(),
        )
        assert result["comment_signal"]["positive_count"] >= 1

    def test_negative_comment_counted_and_flag_set(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(comments=["Total scam, avoid this seller"]),
            _make_request(),
        )
        assert result["comment_signal"]["negative_count"] >= 1
        assert "negative_comment_signal" in result["warning_flags"]


# ---------------------------------------------------------------------------
# Missing fields and completeness
# ---------------------------------------------------------------------------


class TestCompletenessScore:
    def test_all_fields_present_gives_full_completeness(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(), _make_request())
        assert result["completeness_score"] == 1.0
        assert result["missing_fields"] == []

    def test_missing_title_penalises_completeness(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(title=""), _make_request())
        assert "title" in result["missing_fields"]
        assert result["completeness_score"] < 1.0

    def test_missing_price_and_description_penalises(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(price=None, description=""), _make_request()
        )
        assert "price" in result["missing_fields"]
        assert "description" in result["missing_fields"]
        assert result["completeness_score"] < 0.7


# ---------------------------------------------------------------------------
# Match level thresholds
# ---------------------------------------------------------------------------


class TestMatchLevel:
    def test_high_score_gives_matched(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(title="iPhone 13 Pro sealed box"),
            _make_request(query_text="iphone"),
        )
        # With query text match and full completeness, score should be >= 0.70
        assert result["match_level"] in ("matched", "partially_matched")

    def test_weak_post_gives_weak_or_partially_matched(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(
            _make_post(
                title="",
                description="",
                price=None,
                seller_name="",
                location="",
                images=[],
            ),
            _make_request(query_text="iphone", require_image=False),
        )
        assert result["match_level"] in ("weak_match", "partially_matched")

    def test_logic_summary_not_empty(self):
        analyzer = LogicAnalyzer()
        result = analyzer.analyze(_make_post(), _make_request())
        assert isinstance(result["logic_summary"], str)
        assert len(result["logic_summary"]) > 0


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


class TestUtilFunctions:
    def test_text_or_empty_strips_value(self):
        assert _text_or_empty("  hello  ") == "hello"

    def test_text_or_empty_returns_empty_for_none(self):
        assert _text_or_empty(None) == ""

    def test_list_or_empty_returns_list(self):
        assert _list_or_empty(["a", "b"]) == ["a", "b"]

    def test_list_or_empty_returns_empty_for_non_list(self):
        assert _list_or_empty("not a list") == []

    def test_list_or_empty_filters_blank_items(self):
        assert _list_or_empty(["a", "", "  "]) == ["a"]

    def test_safe_float_converts_int(self):
        assert _safe_float(100) == 100.0

    def test_safe_float_converts_string(self):
        assert _safe_float("99.5") == 99.5

    def test_safe_float_returns_none_for_none(self):
        assert _safe_float(None) is None

    def test_safe_float_returns_none_for_invalid(self):
        assert _safe_float("abc") is None

    def test_normalize_key_lowercases_and_strips(self):
        assert _normalize_key("  iPhone 13  ") == "iphone 13"

    def test_normalize_key_collapses_spaces(self):
        assert _normalize_key("hello   world") == "hello world"
