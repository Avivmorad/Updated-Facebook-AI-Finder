from app.logic.input_normalization import (
    normalize_to_search_request,
    _normalize_text_list,
    _merge_regions,
)
from app.models.input_models import RawSearchInput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw(
    main_text: str = "iPhone",
    all_country: bool = True,
    **kwargs,
) -> RawSearchInput:
    defaults = dict(
        main_text=main_text,
        tags=[],
        secondary_attributes=[],
        forbidden_words=[],
        min_price=None,
        max_price=None,
        is_free=False,
        post_age="24h",
        require_image=True,
        language="he",
        regions=[],
        manual_regions=[],
        all_country=all_country,
        group_mode="all_groups",
        groups=[],
        group_sources=["user_groups"],
        group_urls=[],
        select_all_groups=False,
        search_name=None,
    )
    defaults.update(kwargs)
    return RawSearchInput(**defaults)


# ---------------------------------------------------------------------------
# normalize_to_search_request
# ---------------------------------------------------------------------------


class TestNormalizeToSearchRequest:
    def test_query_text_stripped(self):
        raw = _make_raw(main_text="  MacBook Pro  ")
        result = normalize_to_search_request(raw)
        assert result.query_text == "MacBook Pro"

    def test_language_lowercased_and_stripped(self):
        raw = _make_raw(language="  HE  ")
        result = normalize_to_search_request(raw)
        assert result.language == "he"

    def test_language_defaults_when_empty(self):
        raw = _make_raw(language="")
        result = normalize_to_search_request(raw)
        # Should fall back to DEFAULT_LANGUAGE ("he")
        assert result.language == "he"

    def test_is_free_sets_max_price_zero_and_min_none(self):
        raw = _make_raw(is_free=True, min_price=None, max_price=None)
        result = normalize_to_search_request(raw)
        assert result.min_price is None
        assert result.max_price == 0.0

    def test_not_free_preserves_prices(self):
        raw = _make_raw(is_free=False, min_price=100.0, max_price=500.0)
        result = normalize_to_search_request(raw)
        assert result.min_price == 100.0
        assert result.max_price == 500.0

    def test_is_free_overrides_existing_prices(self):
        raw = _make_raw(is_free=True, min_price=50.0, max_price=200.0)
        result = normalize_to_search_request(raw)
        assert result.min_price is None
        assert result.max_price == 0.0

    def test_regions_merged_without_duplicates(self):
        raw = _make_raw(
            all_country=False,
            regions=["north", "center"],
            manual_regions=["center", "Tel Aviv"],
        )
        result = normalize_to_search_request(raw)
        assert "north" in result.target_regions
        assert "Tel Aviv" in result.target_regions
        # "center" should appear only once
        assert result.target_regions.count("center") == 1

    def test_all_fields_passed_through(self):
        raw = _make_raw(
            tags=["laptop"],
            secondary_attributes=["silver"],
            forbidden_words=["broken"],
            post_age="7d",
            require_image=False,
            group_mode="specific_groups",
            groups=["Group A"],
            group_sources=["user_groups"],
            group_urls=["https://example.com"],
            select_all_groups=False,
        )
        result = normalize_to_search_request(raw)
        assert result.tags == ["laptop"]
        assert result.secondary_attributes == ["silver"]
        assert result.forbidden_words == ["broken"]
        assert result.post_age == "7d"
        assert result.require_image is False
        assert result.group_mode == "specific_groups"
        assert result.groups == ["Group A"]
        assert result.group_urls == ["https://example.com"]

    def test_to_dict_returns_dict(self):
        raw = _make_raw()
        result = normalize_to_search_request(raw)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "query_text" in d


# ---------------------------------------------------------------------------
# _normalize_text_list
# ---------------------------------------------------------------------------


class TestNormalizeTextList:
    def test_strips_whitespace(self):
        assert _normalize_text_list(["  hello ", "world  "]) == ["hello", "world"]

    def test_filters_empty_strings(self):
        assert _normalize_text_list(["", "  ", "valid"]) == ["valid"]

    def test_empty_input_returns_empty(self):
        assert _normalize_text_list([]) == []


# ---------------------------------------------------------------------------
# _merge_regions
# ---------------------------------------------------------------------------


class TestMergeRegions:
    def test_combines_predefined_and_manual(self):
        result = _merge_regions(["north"], ["Tel Aviv"])
        assert "north" in result
        assert "Tel Aviv" in result

    def test_deduplicates_case_insensitively(self):
        result = _merge_regions(["NORTH"], ["north"])
        assert len(result) == 1

    def test_first_occurrence_is_kept(self):
        result = _merge_regions(["North"], ["north"])
        assert result[0] == "North"

    def test_empty_lists_return_empty(self):
        assert _merge_regions([], []) == []
